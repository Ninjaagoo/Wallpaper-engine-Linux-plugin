// Wallpaper Engine for Wayland - Libadwaita preferences window (GNOME 45+)

import Adw from 'gi://Adw';
import Gdk from 'gi://Gdk';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Gtk from 'gi://Gtk';

import {ExtensionPreferences, gettext as _} from 'resource:///org/gnome/Shell/Extensions/js/extensions/prefs.js';

const VALORES_MECANISMO = ['auto', 'wallpaperengine', 'mpv'];
const rotulosMecanismo = () => [_('Automatic'), _('linux-wallpaperengine'), _('mpv')];

const VALORES_ESCALA = ['fit', 'fill', 'stretch'];
const rotulosEscala = () => [_('Fit (letterbox)'), _('Fill (crop)'), _('Stretch')];

const VALORES_FPS = [30, 60];
const ROTULOS_FPS = ['30 FPS', '60 FPS'];

function shortenPath(caminho) {
    const diretorioUsuario = GLib.get_home_dir();
    if (caminho.startsWith(diretorioUsuario))
        return `~${caminho.slice(diretorioUsuario.length)}`;
    return caminho;
}

export default class WallpaperEnginePrefs extends ExtensionPreferences {
    fillPreferencesWindow(janela) {
        const configuracoes = this.getSettings();
        janela.set_default_size(680, 780);
        janela.set_search_enabled(true);

        const pagina = new Adw.PreferencesPage({
            title: _('Wallpaper'),
            icon_name: 'preferences-desktop-wallpaper-symbolic',
        });
        janela.add(pagina);

        pagina.add(this._buildGeneralGroup(configuracoes));
        pagina.add(this._buildVideoGroup(configuracoes, janela));
        pagina.add(this._buildWallpaperEngineGroup(configuracoes, janela));
        pagina.add(this._buildPlaybackGroup(configuracoes));
        pagina.add(this._buildDisplayGroup(configuracoes));
    }

    // ------------------------------------------------------------------ groups

    _buildGeneralGroup(configuracoes) {
        const grupo = new Adw.PreferencesGroup({
            title: _('General'),
        });

        const linhaAtivacao = new Adw.SwitchRow({
            title: _('Animated Wallpaper'),
            subtitle: _('Master switch for the wallpaper engine process'),
        });
        configuracoes.bind('enabled', linhaAtivacao, 'active', Gio.SettingsBindFlags.DEFAULT);
        grupo.add(linhaAtivacao);

        const linhaMecanismo = new Adw.ComboRow({
            title: _('Rendering Engine'),
            subtitle: _('Automatic uses linux-wallpaperengine for Workshop scenes, mpv otherwise'),
            model: Gtk.StringList.new(rotulosMecanismo()),
        });
        this._bindComboToStringSetting(configuracoes, 'engine', linhaMecanismo, VALORES_MECANISMO);
        grupo.add(linhaMecanismo);

        return grupo;
    }

    _buildVideoGroup(configuracoes, janela) {
        const grupo = new Adw.PreferencesGroup({
            title: _('Video Wallpaper (mpv)'),
            description: _('Local MP4, WebM, MKV or GIF played with hardware-accelerated mpv'),
        });

        const linhaVideo = new Adw.ActionRow({
            title: _('Video File'),
            activatable: true,
        });
        const atualizarSubtituloVideo = () => {
            const caminho = configuracoes.get_string('video-path');
            linhaVideo.set_subtitle(caminho === '' ? _('No file selected') : shortenPath(caminho));
        };
        atualizarSubtituloVideo();
        configuracoes.connect('changed::video-path', atualizarSubtituloVideo);

        const botaoLimpar = new Gtk.Button({
            icon_name: 'edit-clear-symbolic',
            tooltip_text: _('Clear selection'),
            valign: Gtk.Align.CENTER,
            css_classes: ['flat'],
        });
        botaoLimpar.connect('clicked', () => configuracoes.set_string('video-path', ''));

        const botaoProcurar = new Gtk.Button({
            icon_name: 'document-open-symbolic',
            tooltip_text: _('Choose a video file'),
            valign: Gtk.Align.CENTER,
            css_classes: ['flat'],
        });
        const abrirDialogoVideo = () => {
            const filtro = new Gtk.FileFilter();
            filtro.set_name(_('Videos and GIFs'));
            filtro.add_mime_type('video/mp4');
            filtro.add_mime_type('video/webm');
            filtro.add_mime_type('video/x-matroska');
            filtro.add_mime_type('image/gif');

            const filtroTodos = new Gtk.FileFilter();
            filtroTodos.set_name(_('All files'));
            filtroTodos.add_pattern('*');

            const filtros = new Gio.ListStore({item_type: Gtk.FileFilter});
            filtros.append(filtro);
            filtros.append(filtroTodos);

            const dialogo = new Gtk.FileDialog({
                title: _('Select a Video Wallpaper'),
                modal: true,
                filters: filtros,
                default_filter: filtro,
            });
            dialogo.open(janela, null, (dialogoAberto, resultado) => {
                try {
                    const arquivo = dialogoAberto.open_finish(resultado);
                    if (arquivo !== null)
                        configuracoes.set_string('video-path', arquivo.get_path());
                } catch (_erro) {
                    // Dialog dismissed by the user.
                }
            });
        };
        botaoProcurar.connect('clicked', abrirDialogoVideo);
        linhaVideo.connect('activated', abrirDialogoVideo);

        linhaVideo.add_suffix(botaoLimpar);
        linhaVideo.add_suffix(botaoProcurar);
        grupo.add(linhaVideo);

        const linhaCaminhoMpv = new Adw.EntryRow({
            title: _('mpv Command'),
        });
        configuracoes.bind('mpv-path', linhaCaminhoMpv, 'text', Gio.SettingsBindFlags.DEFAULT);
        grupo.add(linhaCaminhoMpv);

        return grupo;
    }

    _buildWallpaperEngineGroup(configuracoes, janela) {
        const grupo = new Adw.PreferencesGroup({
            title: _('Steam Wallpaper Engine'),
            description: _('Workshop scenes rendered with linux-wallpaperengine'),
        });

        const linhaIdentificador = new Adw.EntryRow({
            title: _('Workshop Item ID or Scene Path'),
        });
        configuracoes.bind('wallpaper-id', linhaIdentificador, 'text', Gio.SettingsBindFlags.DEFAULT);
        grupo.add(linhaIdentificador);

        grupo.add(this._buildFolderRow(
            configuracoes, janela, 'workshop-path',
            _('Workshop Content Folder'),
            _('Select the Steam Workshop Content Folder')));

        grupo.add(this._buildFolderRow(
            configuracoes, janela, 'assets-path',
            _('Assets Folder (optional)'),
            _('Select the Wallpaper Engine Assets Folder')));

        const linhaExecutavel = new Adw.EntryRow({
            title: _('linux-wallpaperengine Command'),
        });
        configuracoes.bind('wallpaperengine-path', linhaExecutavel, 'text', Gio.SettingsBindFlags.DEFAULT);
        grupo.add(linhaExecutavel);

        return grupo;
    }

    _buildFolderRow(configuracoes, janela, chave, titulo, tituloDialogo) {
        const linha = new Adw.ActionRow({
            title: titulo,
            activatable: true,
        });
        const atualizarSubtitulo = () => {
            const caminho = configuracoes.get_string(chave);
            linha.set_subtitle(caminho === '' ? _('Not set') : shortenPath(caminho));
        };
        atualizarSubtitulo();
        configuracoes.connect(`changed::${chave}`, atualizarSubtitulo);

        const botaoLimpar = new Gtk.Button({
            icon_name: 'edit-clear-symbolic',
            tooltip_text: _('Clear selection'),
            valign: Gtk.Align.CENTER,
            css_classes: ['flat'],
        });
        botaoLimpar.connect('clicked', () => configuracoes.set_string(chave, ''));

        const botaoProcurar = new Gtk.Button({
            icon_name: 'folder-open-symbolic',
            tooltip_text: _('Choose a folder'),
            valign: Gtk.Align.CENTER,
            css_classes: ['flat'],
        });
        const abrirDialogoPasta = () => {
            const dialogo = new Gtk.FileDialog({
                title: tituloDialogo,
                modal: true,
            });
            dialogo.select_folder(janela, null, (dialogoAberto, resultado) => {
                try {
                    const pasta = dialogoAberto.select_folder_finish(resultado);
                    if (pasta !== null)
                        configuracoes.set_string(chave, pasta.get_path());
                } catch (_erro) {
                    // Dialog dismissed by the user.
                }
            });
        };
        botaoProcurar.connect('clicked', abrirDialogoPasta);
        linha.connect('activated', abrirDialogoPasta);

        linha.add_suffix(botaoLimpar);
        linha.add_suffix(botaoProcurar);
        return linha;
    }

    _buildPlaybackGroup(configuracoes) {
        const grupo = new Adw.PreferencesGroup({
            title: _('Playback'),
        });

        const linhaSilenciar = new Adw.SwitchRow({
            title: _('Mute Audio'),
        });
        configuracoes.bind('mute', linhaSilenciar, 'active', Gio.SettingsBindFlags.DEFAULT);
        grupo.add(linhaSilenciar);

        const linhaVolume = new Adw.SpinRow({
            title: _('Volume'),
            subtitle: _('Audio volume in percent when not muted'),
            adjustment: new Gtk.Adjustment({
                lower: 0,
                upper: 100,
                step_increment: 5,
                page_increment: 10,
            }),
        });
        configuracoes.bind('volume', linhaVolume, 'value', Gio.SettingsBindFlags.DEFAULT);
        configuracoes.bind('mute', linhaVolume, 'sensitive',
            Gio.SettingsBindFlags.GET | Gio.SettingsBindFlags.INVERT_BOOLEAN);
        grupo.add(linhaVolume);

        const linhaFps = new Adw.ComboRow({
            title: _('FPS Cap'),
            subtitle: _('Lower values save GPU/CPU and battery'),
            model: Gtk.StringList.new(ROTULOS_FPS),
        });
        const fpsAtual = configuracoes.get_int('fps');
        const indiceFps = VALORES_FPS.indexOf(fpsAtual);
        linhaFps.set_selected(indiceFps >= 0 ? indiceFps : 1);
        linhaFps.connect('notify::selected', () => {
            configuracoes.set_int('fps', VALORES_FPS[linhaFps.get_selected()]);
        });
        grupo.add(linhaFps);

        const linhaEscala = new Adw.ComboRow({
            title: _('Scaling Mode'),
            model: Gtk.StringList.new(rotulosEscala()),
        });
        this._bindComboToStringSetting(configuracoes, 'scaling', linhaEscala, VALORES_ESCALA);
        grupo.add(linhaEscala);

        return grupo;
    }

    _buildDisplayGroup(configuracoes) {
        const grupo = new Adw.PreferencesGroup({
            title: _('Display'),
        });

        const rotulos = [_('Primary Monitor')];
        const tela = Gdk.Display.get_default();
        if (tela !== null) {
            const monitores = tela.get_monitors();
            for (let i = 0; i < monitores.get_n_items(); i++) {
                const monitor = monitores.get_item(i);
                const conector = monitor.get_connector() ?? _('Unknown');
                const descricao = monitor.get_description() ?? '';
                rotulos.push(descricao !== ''
                    ? `${i}: ${descricao} (${conector})`
                    : `${i}: ${conector}`);
            }
        }

        const linhaMonitor = new Adw.ComboRow({
            title: _('Target Monitor'),
            subtitle: _('Which monitor the animated wallpaper is rendered on'),
            model: Gtk.StringList.new(rotulos),
        });
        const indiceAtual = configuracoes.get_int('monitor-index');
        linhaMonitor.set_selected(
            indiceAtual >= 0 && indiceAtual + 1 < rotulos.length ? indiceAtual + 1 : 0);
        linhaMonitor.connect('notify::selected', () => {
            const selecionado = linhaMonitor.get_selected();
            configuracoes.set_int('monitor-index', selecionado === 0 ? -1 : selecionado - 1);
        });
        grupo.add(linhaMonitor);

        return grupo;
    }

    // ----------------------------------------------------------------- helpers

    _bindComboToStringSetting(configuracoes, chave, linhaSelecao, valores) {
        const atual = configuracoes.get_string(chave);
        const i = valores.indexOf(atual);
        linhaSelecao.set_selected(i >= 0 ? i : 0);
        linhaSelecao.connect('notify::selected', () => {
            configuracoes.set_string(chave, valores[linhaSelecao.get_selected()]);
        });
    }
}
