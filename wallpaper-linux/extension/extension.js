// Wallpaper Engine for Wayland - GNOME Shell extension
// Spawns linux-wallpaperengine or mpv as a background renderer process and
// embeds its window into GNOME Shell's background group so it sits strictly
// behind desktop icons and application windows.

import GLib from 'gi://GLib';
import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import Meta from 'gi://Meta';

import {Extension, InjectionManager} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as Background from 'resource:///org/gnome/shell/ui/background.js';
import {Workspace} from 'resource:///org/gnome/shell/ui/workspace.js';
import {WorkspaceThumbnail} from 'resource:///org/gnome/shell/ui/workspaceThumbnail.js';

const ID_APLICATIVO_MPV = 'gwe-mpv-renderer';
const CLASSES_JANELA_RENDERIZADOR = [
    ID_APLICATIVO_MPV,
    'linux-wallpaperengine',
    'wallpaperengine',
    'linux-wallpaperengine-window',
];

// Bumped on every code change; logged from enable() so we can tell which
// revision the running shell actually loaded (see the comment there).
const REVISAO_CODIGO = 13;

const SIGTERM = 15;
const SIGCONT = 12; // launcher: unpause container
const SIGSTOP = 10; // launcher: pause container

const INTERVALO_REINICIO_MS = 700;
const INTERVALO_RETENTATIVA_MS = 2000;
const MAXIMO_RETENTATIVAS = 3;
const TEMPO_ESTAVEL_US = 30 * 1000 * 1000; // 30s uptime resets the retry counter
const TENTATIVAS_BUSCA_JANELA = 20;
const INTERVALO_BUSCA_JANELA_MS = 100;

function expandTilde(caminho) {
    if (caminho.startsWith('~/'))
        return GLib.build_filenamev([GLib.get_home_dir(), caminho.slice(2)]);
    if (caminho === '~')
        return GLib.get_home_dir();
    return caminho;
}

export default class WallpaperEngineExtension extends Extension {
    enable() {
        this._configuracoes = this.getSettings();
        this._destruido = false;

        this._processo = null;
        this._clienteWayland = null;
        this._processoParando = false;
        this._reinicioPendente = false;
        this._inicioProcesso = 0;
        this._pausado = false;
        this._retentativas = 0;

        // Deliberately at warning level so it always reaches the journal:
        // on Wayland the shell never re-imports extension code within a
        // session, so this is how we verify which revision is actually live.
        console.warn(`[wallpaperengine@waylandwe] enabled, code revision ${REVISAO_CODIGO}`);

        this._janelaRenderizador = null;
        this._atorRenderizador = null;
        this._copiasWallpaper = new Set();
        this._atoresFundo = new Map();
        this._idRemocaoRenderizador = 0;
        this._idElevacaoRenderizador = 0;
        this._idVisibilidadeRenderizador = 0;

        this._idTemporizadorReinicio = 0;
        this._idTemporizadorRetentativa = 0;
        this._idTempoLimiteEncerramento = 0;
        this._temporizadoresBusca = new Set();

        this._gerenciadorInjecao = new InjectionManager();
        this._installOverviewHiding();

        this._idCriacaoJanela = global.display.connect(
            'window-created', (_tela, janela) => this._onWindowCreated(janela));

        this._idAlteracaoMonitores = Main.layoutManager.connect(
            'monitors-changed', () => this._scheduleRestart());

        this._idAlteracaoConfiguracoes = this._configuracoes.connect(
            'changed', () => this._scheduleRestart());

        // Suspend rendering while the screensaver / screen blank is active.
        // (The full lock screen additionally disables this extension entirely
        // because metadata.json only declares the "user" session mode.)
        this._idProtetorTela = Gio.DBus.session.signal_subscribe(
            'org.gnome.ScreenSaver',
            'org.gnome.ScreenSaver',
            'ActiveChanged',
            '/org/gnome/ScreenSaver',
            null,
            Gio.DBusSignalFlags.NONE,
            (_conexao, _remetente, _caminho, _interface, _sinal, parametros) => {
                const [ativo] = parametros.deep_unpack();
                this._setPaused(ativo);
            });

        if (this._configuracoes.get_boolean('enabled'))
            this._startEngine();
    }

    disable() {
        this._destruido = true;
        this._reinicioPendente = false;

        if (this._gerenciadorInjecao) {
            this._gerenciadorInjecao.clear();
            this._gerenciadorInjecao = null;
        }

        if (this._idCriacaoJanela) {
            global.display.disconnect(this._idCriacaoJanela);
            this._idCriacaoJanela = 0;
        }
        if (this._idAlteracaoMonitores) {
            Main.layoutManager.disconnect(this._idAlteracaoMonitores);
            this._idAlteracaoMonitores = 0;
        }
        if (this._idAlteracaoConfiguracoes) {
            this._configuracoes.disconnect(this._idAlteracaoConfiguracoes);
            this._idAlteracaoConfiguracoes = 0;
        }
        if (this._idProtetorTela) {
            Gio.DBus.session.signal_unsubscribe(this._idProtetorTela);
            this._idProtetorTela = 0;
        }

        this._clearTimeouts();
        this._stopEngine(true);
        for (const [ator, id] of this._atoresFundo)
            ator.disconnect(id);
        this._atoresFundo.clear();

        this._configuracoes = null;
    }

    // Hide the renderer window from the Overview grid, workspace thumbnails
    // and Alt-Tab. Without this GNOME treats it like any other normal
    // window: it shows up as a selectable tile, and clicking/hovering into
    // it makes GNOME try to focus a window that isn't really meant to be
    // interacted with, which looks like an involuntary Alt-Tab.
    _installOverviewHiding() {
        // The matcher must work the moment the window first appears (the
        // Overview registers new windows before our polling-based adoption
        // finishes), hence _windowMatchesRenderer rather than only checking
        // the adopted-window reference. Never let an exception escape into
        // the shell's UI code: misidentifying a window as "not ours" only
        // shows an extra tile, while a thrown error breaks the Overview.
        const ehRenderizador = janela => {
            try {
                return this._windowMatchesRenderer(janela);
            } catch (_erro) {
                return false;
            }
        };

        this._gerenciadorInjecao.overrideMethod(Workspace.prototype, '_isOverviewWindow',
            metodoOriginal => function (janela) {
                return ehRenderizador(janela) ? false : metodoOriginal.apply(this, [janela]);
            });

        this._gerenciadorInjecao.overrideMethod(WorkspaceThumbnail.prototype, '_isOverviewWindow',
            metodoOriginal => function (janela) {
                return ehRenderizador(janela) ? false : metodoOriginal.apply(this, [janela]);
            });

        this._gerenciadorInjecao.overrideMethod(Meta.Display.prototype, 'get_tab_list',
            metodoOriginal => function (tipo, areaTrabalho) {
                return metodoOriginal.apply(this, [tipo, areaTrabalho])
                    .filter(janela => !ehRenderizador(janela));
            });

        const extensao = this;
        this._gerenciadorInjecao.overrideMethod(Background.BackgroundManager.prototype,
            '_createBackgroundActor', metodoOriginal => function () {
                const ator = metodoOriginal.call(this);
                extensao._trackBackground(ator);
                return ator;
            });
        for (const ator of Main.layoutManager._backgroundGroup.get_children())
            this._trackBackground(ator);
        // Include backgrounds already created for the overview before enable().
        Main.overview._overview?._controls?._workspacesDisplay?._updateWorkspacesViews?.();
    }

    _trackBackground(fundo) {
        if (!(fundo instanceof Meta.BackgroundActor) || this._atoresFundo.has(fundo))
            return;
        const id = fundo.connect('destroy', () => this._atoresFundo.delete(fundo));
        this._atoresFundo.set(fundo, id);
        this._attachClone(fundo);
    }

    _attachClone(fundo) {
        if (!this._atorRenderizador || this._destruido || fundo.monitor !== this._targetMonitorIndex())
            return;
        if ([...this._copiasWallpaper].some(componente => componente.get_parent() === fundo))
            return;
        const copia = new Clutter.Clone({source: this._atorRenderizador, reactive: false});
        copia.add_constraint(new Clutter.BindConstraint({
            source: fundo, coordinate: Clutter.BindCoordinate.SIZE,
        }));
        copia.connect('destroy', () => this._copiasWallpaper.delete(copia));
        fundo.add_child(copia);
        this._copiasWallpaper.add(copia);
    }

    _clearTimeouts() {
        if (this._idTemporizadorReinicio) {
            GLib.source_remove(this._idTemporizadorReinicio);
            this._idTemporizadorReinicio = 0;
        }
        if (this._idTemporizadorRetentativa) {
            GLib.source_remove(this._idTemporizadorRetentativa);
            this._idTemporizadorRetentativa = 0;
        }
        if (this._idTempoLimiteEncerramento) {
            GLib.source_remove(this._idTempoLimiteEncerramento);
            this._idTempoLimiteEncerramento = 0;
        }
        for (const id of this._temporizadoresBusca)
            GLib.source_remove(id);
        this._temporizadoresBusca.clear();
    }

    // ---------------------------------------------------------------- geometry

    _targetMonitorIndex() {
        const monitores = Main.layoutManager.monitors;
        let i = this._configuracoes.get_int('monitor-index');
        if (i < 0 || i >= monitores.length)
            i = Main.layoutManager.primaryIndex;
        return i;
    }

    _targetGeometry() {
        const monitor = Main.layoutManager.monitors[this._targetMonitorIndex()];
        return {
            x: monitor.x,
            y: monitor.y,
            width: monitor.width,
            height: monitor.height,
        };
    }

    // ------------------------------------------------------------ command line

    _resolveEngine() {
        const mecanismo = this._configuracoes.get_string('engine');
        if (mecanismo !== 'auto')
            return mecanismo;

        const cenaConfigurada = this._configuracoes.get_string('wallpaper-id').trim() !== '';
        const executavelWallpaper = expandTilde(this._configuracoes.get_string('wallpaperengine-path'));
        const wallpaperEncontrado = GLib.path_is_absolute(executavelWallpaper)
            ? GLib.file_test(executavelWallpaper, GLib.FileTest.IS_EXECUTABLE)
            : GLib.find_program_in_path(executavelWallpaper) !== null;

        if (cenaConfigurada && wallpaperEncontrado)
            return 'wallpaperengine';
        return 'mpv';
    }

    _resolveScenePath() {
        const bruto = this._configuracoes.get_string('wallpaper-id').trim();
        if (bruto === '')
            return null;

        if (/^\d+$/.test(bruto)) {
            const workshop = expandTilde(this._configuracoes.get_string('workshop-path'));
            const candidato = GLib.build_filenamev([workshop, bruto]);
            if (GLib.file_test(candidato, GLib.FileTest.EXISTS))
                return candidato;
            // Let linux-wallpaperengine try to locate the bare ID itself.
            return bruto;
        }
        return expandTilde(bruto);
    }

    _buildWallpaperEngineArgv() {
        const cena = this._resolveScenePath();
        if (cena === null) {
            this._notifyError(
                'No Wallpaper Engine scene configured. Set a Workshop item ID or scene path in the extension preferences.');
            return null;
        }

        const geometria = this._targetGeometry();
        const fps = this._configuracoes.get_int('fps');
        const escala = this._configuracoes.get_string('scaling');
        const argumentos = [
            expandTilde(this._configuracoes.get_string('wallpaperengine-path')),
            '--fps', String(fps),
            '--scaling', escala,
            // GNOME's Mutter does not implement wlr-layer-shell, so the
            // engine renders into a normal window sized to the monitor; the
            // extension then reparents that window behind the desktop.
            '--window', `0x0x${geometria.width}x${geometria.height}`,
        ];

        if (this._configuracoes.get_boolean('mute'))
            argumentos.push('--silent');
        else
            argumentos.push('--volume', String(this._configuracoes.get_int('volume')));

        const recursos = expandTilde(this._configuracoes.get_string('assets-path').trim());
        if (recursos !== '')
            argumentos.push('--assets-dir', recursos);

        argumentos.push(cena);
        return argumentos;
    }

    _buildMpvArgv() {
        const video = expandTilde(this._configuracoes.get_string('video-path').trim());
        if (video === '') {
            this._notifyError(
                'No video file configured. Pick an MP4/WebM/GIF in the extension preferences.');
            return null;
        }
        if (!GLib.file_test(video, GLib.FileTest.EXISTS)) {
            this._notifyError(`Video file not found: ${video}`);
            return null;
        }

        const geometria = this._targetGeometry();
        const escala = this._configuracoes.get_string('scaling');
        const silenciado = this._configuracoes.get_boolean('mute');
        const volume = this._configuracoes.get_int('volume');

        const argumentos = [
            expandTilde(this._configuracoes.get_string('mpv-path')),
            '--no-config',
            '--really-quiet',
            '--force-window=yes',
            '--no-border',
            '--no-osc',
            '--no-osd-bar',
            '--no-input-default-bindings',
            '--input-vo-keyboard=no',
            '--no-input-cursor',
            '--cursor-autohide=no',
            '--no-stop-screensaver',
            '--no-audio-display',
            '--hwdec=auto-safe',
            '--loop-file=inf',
            `--title=${ID_APLICATIVO_MPV}`,
            `--wayland-app-id=${ID_APLICATIVO_MPV}`,
            `--x11-name=${ID_APLICATIVO_MPV}`,
            `--geometry=${geometria.width}x${geometria.height}`,
            '--auto-window-resize=no',
            '--keepaspect-window=no',
            `--volume=${volume}`,
            silenciado ? '--mute=yes' : '--mute=no',
        ];

        if (escala === 'fill')
            argumentos.push('--panscan=1.0');
        else if (escala === 'stretch')
            argumentos.push('--keepaspect=no');

        argumentos.push(video);
        return argumentos;
    }

    // ------------------------------------------------------- process lifecycle

    _startEngine() {
        // GNOME restores enabled extensions independently of XDG autostart.
        // Honor the preference even after a manual launch in the previous login.
        try {
            const caminhoConfiguracao = `${GLib.get_home_dir()}/.config/wallpaper-engine/config.json`;
            const [encontrado, dados] = GLib.file_get_contents(caminhoConfiguracao);
            if (encontrado && JSON.parse(new TextDecoder().decode(dados)).autostart === false) {
                const [, processoAtual] = GLib.file_get_contents('/proc/self/stat');
                const pid = new TextDecoder().decode(processoAtual).split(' ')[0];
                const marcador = `${GLib.get_user_runtime_dir()}/wallpaper-engine-manual-session`;
                if (!GLib.file_test(marcador, GLib.FileTest.EXISTS))
                    return;
                const [, permitido] = GLib.file_get_contents(marcador);
                if (!new TextDecoder().decode(permitido).trim().split(/\s+/).includes(pid))
                    return;
            }
        } catch (erro) {
            // Existing installations without a config keep their original behavior.
            if (GLib.file_test(`${GLib.get_home_dir()}/.config/wallpaper-engine/config.json`, GLib.FileTest.EXISTS)) {
                console.warn(`Wallpaper startup preference could not be read: ${erro}`);
                return;
            }
        }

        if (this._processo !== null || this._destruido)
            return;
        if (Main.layoutManager.monitors.length === 0)
            return;

        const mecanismo = this._resolveEngine();
        const argumentos = mecanismo === 'wallpaperengine'
            ? this._buildWallpaperEngineArgv()
            : this._buildMpvArgv();
        if (argumentos === null)
            return;

        // Prefer spawning through Meta.WaylandClient: Mutter then knows the
        // window belongs to a compositor-private client, and owns_window()
        // gives us exact, race-free identification of the renderer window
        // (mpv reports no usable wm_class/app-id on Wayland, and PID matching
        // only works after the window exists). Fall back to a plain
        // subprocess if that fails (e.g. X11 session).
        let processo = null;
        this._clienteWayland = null;
        try {
            const opcoes = Gio.SubprocessFlags.STDOUT_SILENCE |
                Gio.SubprocessFlags.STDERR_SILENCE;
            if (Meta.is_wayland_compositor()) {
                const iniciador = new Gio.SubprocessLauncher({flags: opcoes});
                this._clienteWayland =
                    Meta.WaylandClient.new_subprocess(global.context, iniciador, argumentos);
                processo = this._clienteWayland.get_subprocess();
            }
            if (processo === null)
                processo = Gio.Subprocess.new(argumentos, opcoes);
        } catch (erro) {
            this._clienteWayland = null;
            try {
                processo = Gio.Subprocess.new(
                    argumentos,
                    Gio.SubprocessFlags.STDOUT_SILENCE | Gio.SubprocessFlags.STDERR_SILENCE);
            } catch (erroSecundario) {
                this._notifyError(
                    `Failed to launch "${argumentos[0]}": ${erroSecundario.message}. ` +
                    'Check that the binary is installed (see scripts/install-fedora.sh).');
                return;
            }
        }

        this._processo = processo;
        this._processoParando = false;
        this._pausado = false;
        this._inicioProcesso = GLib.get_monotonic_time();

        processo.wait_async(null, (propriedade, resultado) => {
            try {
                propriedade.wait_finish(resultado);
            } catch (_erro) {
                // Cancelled or reaping failed; treat as exit.
            }
            this._onEngineExited(propriedade);
        });
    }

    _onEngineExited(processo) {
        if (processo !== this._processo || this._destruido)
            return;

        const estavaParando = this._processoParando;
        if (this._idTempoLimiteEncerramento) {
            GLib.source_remove(this._idTempoLimiteEncerramento);
            this._idTempoLimiteEncerramento = 0;
        }
        const tempoAtivo = GLib.get_monotonic_time() - this._inicioProcesso;
        this._processo = null;
        this._clienteWayland = null;
        this._processoParando = false;
        this._pausado = false;
        this._forgetWindow();

        if (estavaParando) {
            const reiniciar = this._reinicioPendente;
            this._reinicioPendente = false;
            if (reiniciar && this._configuracoes?.get_boolean('enabled'))
                this._startEngine();
            return;
        }

        if (tempoAtivo > TEMPO_ESTAVEL_US)
            this._retentativas = 0;

        if (this._retentativas < MAXIMO_RETENTATIVAS) {
            this._retentativas++;
            this._idTemporizadorRetentativa = GLib.timeout_add(
                GLib.PRIORITY_DEFAULT, INTERVALO_RETENTATIVA_MS, () => {
                    this._idTemporizadorRetentativa = 0;
                    if (this._configuracoes?.get_boolean('enabled'))
                        this._startEngine();
                    return GLib.SOURCE_REMOVE;
                });
        } else {
            this._notifyError(
                'The wallpaper engine process keeps crashing and has been stopped. ' +
                'Check your scene/video settings, then toggle the extension to retry.');
        }
    }

    _stopEngine(imediato = false) {
        if (this._idTemporizadorRetentativa) {
            GLib.source_remove(this._idTemporizadorRetentativa);
            this._idTemporizadorRetentativa = 0;
        }
        for (const id of this._temporizadoresBusca)
            GLib.source_remove(id);
        this._temporizadoresBusca.clear();

        this._forgetWindow();

        const processo = this._processo;
        if (processo === null)
            return;
        if (this._processoParando)
            return;

        this._processoParando = true;

        if (this._pausado) {
            try {
                processo.send_signal(SIGCONT);
            } catch (_erro) {
                // Process already gone.
            }
            this._pausado = false;
        }

        if (imediato) {
            processo.send_signal(SIGTERM);
            return;
        }

        try {
            processo.send_signal(SIGTERM);
        } catch (_erro) {
            return;
        }

        this._idTempoLimiteEncerramento = GLib.timeout_add(
            GLib.PRIORITY_DEFAULT, 3000, () => {
                this._idTempoLimiteEncerramento = 0;
                if (this._processo === processo && this._processoParando)
                    processo.force_exit();
                return GLib.SOURCE_REMOVE;
            });
    }

    _scheduleRestart() {
        if (this._destruido)
            return;
        if (this._idTemporizadorReinicio) {
            GLib.source_remove(this._idTemporizadorReinicio);
            this._idTemporizadorReinicio = 0;
        }
        this._idTemporizadorReinicio = GLib.timeout_add(
            GLib.PRIORITY_DEFAULT, INTERVALO_REINICIO_MS, () => {
                this._idTemporizadorReinicio = 0;
                this._retentativas = 0;
                this._reinicioPendente = this._configuracoes?.get_boolean('enabled') ?? false;
                if (this._processo !== null) {
                    this._stopEngine();
                } else if (this._reinicioPendente) {
                    this._reinicioPendente = false;
                    this._startEngine();
                }
                return GLib.SOURCE_REMOVE;
            });
    }

    _setPaused(pausado) {
        if (this._processo === null || this._processoParando || pausado === this._pausado)
            return;
        try {
            this._processo.send_signal(pausado ? SIGSTOP : SIGCONT);
            this._pausado = pausado;
        } catch (_erro) {
            // Process already gone; the exit handler will clean up.
        }
    }

    // -------------------------------------------------------- window embedding

    _onWindowCreated(janela) {
        if (this._processo === null || this._janelaRenderizador !== null || this._destruido)
            return;

        // wm_class / app-id and title may not be set at creation time on
        // Wayland; poll briefly before giving up on this window.
        let tentativas = 0;
        const idOrigem = GLib.timeout_add(
            GLib.PRIORITY_DEFAULT, INTERVALO_BUSCA_JANELA_MS, () => {
                tentativas++;
                const concluido = this._tryAdoptWindow(janela);
                if (concluido || tentativas >= TENTATIVAS_BUSCA_JANELA) {
                    this._temporizadoresBusca.delete(idOrigem);
                    return GLib.SOURCE_REMOVE;
                }
                return GLib.SOURCE_CONTINUE;
            });
        this._temporizadoresBusca.add(idOrigem);
    }

    _windowMatchesRenderer(janela) {
        if (janela == null)
            return false;

        // Callers aren't consistent about what they hand us: Workspace's
        // _isOverviewWindow passes a MetaWindow, WorkspaceThumbnail's passes
        // a MetaWindowActor. Accept both.
        if (typeof janela.get_meta_window === 'function')
            janela = janela.get_meta_window();
        if (janela == null || typeof janela.get_pid !== 'function')
            return false;

        // Already adopted: identity beats every heuristic.
        if (janela === this._janelaRenderizador)
            return true;

        // Authoritative on Wayland: Mutter tracks which client owns the window.
        if (this._clienteWayland !== null) {
            try {
                if (this._clienteWayland.owns_window(janela))
                    return true;
            } catch (_erro) {
                // Client already gone; fall through to the heuristics.
            }
        }

        if (this._processo === null)
            return false;

        const pidProcesso = parseInt(this._processo.get_identifier(), 10);
        if (Number.isInteger(pidProcesso) && janela.get_pid() === pidProcesso)
            return true;

        const classeJanela = (janela.get_wm_class() ?? '').toLowerCase();
        const titulo = (janela.get_title() ?? '').toLowerCase();
        return CLASSES_JANELA_RENDERIZADOR.some(componente =>
            classeJanela === componente.toLowerCase() || titulo === componente.toLowerCase());
    }

    _tryAdoptWindow(janela) {
        if (this._janelaRenderizador !== null || this._destruido)
            return true;
        if (!this._windowMatchesRenderer(janela))
            return false;
        const ator = janela.get_compositor_private();
        if (!ator)
            return false;
        this._janelaRenderizador = janela;
        this._atorRenderizador = ator;
        janela.unmake_above();
        janela.lower();
        const geometria = this._targetGeometry();
        janela.move_resize_frame(false, geometria.x, geometria.y, geometria.width, geometria.height);

        // Keep Mutter's window actor in its original hierarchy. BackgroundActor
        // culling can discard an arbitrary window reparented into BackgroundGroup.
        // Paint a Clone inside each actual background actor instead.
        for (const fundo of this._atoresFundo.keys())
            this._attachClone(fundo);
        // A hidden source can still be painted by Clutter.Clone. This avoids
        // minimize animations and keeps the original window off the desktop.
        this._idVisibilidadeRenderizador = ator.connect('notify::visible', () => {
            if (ator.visible)
                ator.hide();
        });
        ator.hide();
        this._idRemocaoRenderizador = janela.connect('unmanaged', () => this._forgetWindow());
        this._idElevacaoRenderizador = janela.connect_after('raised', () => janela.lower());

        console.warn(`[wallpaperengine@waylandwe] adopted renderer with background clones (revision 9)`);
        return true;
    }

    _forgetWindow() {
        for (const copia of [...this._copiasWallpaper])
            copia.destroy();
        this._copiasWallpaper.clear();
        if (this._janelaRenderizador !== null) {
            if (this._idRemocaoRenderizador)
                this._janelaRenderizador.disconnect(this._idRemocaoRenderizador);
            if (this._idElevacaoRenderizador)
                this._janelaRenderizador.disconnect(this._idElevacaoRenderizador);
        }
        if (this._idVisibilidadeRenderizador && this._atorRenderizador) {
            try {
                this._atorRenderizador.disconnect(this._idVisibilidadeRenderizador);
            } catch (_erro) {
                // Actor may already be disposed if this runs from 'unmanaged'.
            }
        }
        this._idVisibilidadeRenderizador = 0;
        this._idRemocaoRenderizador = 0;
        this._idElevacaoRenderizador = 0;
        this._janelaRenderizador = null;
        this._atorRenderizador = null;
    }

    // ---------------------------------------------------------------- misc

    _notifyError(mensagem) {
        console.error(`[wallpaperengine@waylandwe] ${mensagem}`);
        Main.notify('Wallpaper Engine for Wayland', mensagem);
    }
}
