import Gio from 'gi://Gio';
import St from 'gi://St';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

const COR_FUNDO = '#111';

export default class FirewatchLoginBackground extends Extension {
    enable() {
        this._atores = [];
        const compartilhado = Gio.File.new_for_path('/var/lib/wallpaper-engine-login');
        this._monitorImagem = compartilhado.monitor_directory(Gio.FileMonitorFlags.NONE, null);
        this._monitorImagem.connect('changed', () => this._refresh());
        this._idMonitor = Main.layoutManager.connect('monitors-changed', () => this._refresh());
        this._idInicializacao = Main.layoutManager.connect('startup-complete', () => this._refresh());
        this._refresh();
    }

    _refresh() {
        this._clear();
        const grupo = Main.screenShield?._lockDialogGroup;
        let imagem = Gio.File.new_for_path('/var/lib/wallpaper-engine-login/background.png');
        if (!imagem.query_exists(null))
            imagem = Gio.File.new_for_path(`${this.path}/firewatch.png`);
        if (!grupo || !imagem.query_exists(null))
            return;
        for (const monitor of Main.layoutManager.monitors) {
            const ator = new St.Widget({
                reactive: false,
                x: monitor.x, y: monitor.y,
                width: monitor.width, height: monitor.height,
                style: `background-color: ${COR_FUNDO}; background-image: url("${imagem.get_uri()}"); background-size: cover;`,
            });
            grupo.insert_child_below(ator, null);
            this._atores.push(ator);
        }
        console.log('[firewatch-login] Static login background loaded');
    }

    _clear() {
        for (const ator of this._atores)
            ator.destroy();
        this._atores = [];
    }

    disable() {
        this._monitorImagem?.cancel();
        this._monitorImagem = null;
        Main.layoutManager.disconnect(this._idMonitor);
        Main.layoutManager.disconnect(this._idInicializacao);
        this._clear();
    }
}
