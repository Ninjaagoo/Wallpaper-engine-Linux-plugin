import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const fonte = fs.readFileSync(new URL('../wallpaper-linux/extension/extension.js', import.meta.url), 'utf8');
const saida = fonte.slice(fonte.indexOf('    _onEngineExited('), fonte.indexOf('    _stopEngine('));
const reinicio = fonte.slice(fonte.indexOf('    _scheduleRestart() {'), fonte.indexOf('    _setPaused('));
let executar;
const removidos = [];
const GLib = {
    PRIORITY_DEFAULT: 0, SOURCE_REMOVE: false,
    get_monotonic_time: () => 100,
    source_remove: id => removidos.push(id),
    timeout_add: (_prioridade, _intervalo, acao) => { executar = acao; return 1; },
};
const metodos = vm.runInNewContext(`({${saida},${reinicio}})`, {
    GLib, INTERVALO_REINICIO_MS: 700, TEMPO_ESTAVEL_US: 1000,
    MAXIMO_RETENTATIVAS: 3, INTERVALO_RETENTATIVA_MS: 2000,
});
const processo = {};
let inicios = 0;
let paradas = 0;
const estado = {
    ...metodos, _processo: processo, _destruido: false, _inicioProcesso: 0,
    _configuracoes: {get_boolean: () => true},
    _startEngine() { assert.equal(this._processo, null); inicios++; },
    _stopEngine() { this._processoParando = true; paradas++; },
    _forgetWindow() {},
};
estado._scheduleRestart();
executar();
assert.equal(paradas, 1);
assert.equal(inicios, 0, 'não inicia enquanto o processo anterior estiver ativo');
estado._idTempoLimiteEncerramento = 7;
estado._onEngineExited(processo);
assert.equal(inicios, 1);
assert.ok(removidos.includes(7));
estado._onEngineExited(processo);
assert.equal(inicios, 1, 'callback antigo não reinicia novamente');
estado._scheduleRestart(); executar();
assert.equal(inicios, 2, 'inicia imediatamente se já não houver processo');
estado._processo = processo;
estado._processoParando = true;
estado._reinicioPendente = false;
estado._onEngineExited(processo);
assert.equal(inicios, 2, 'parada sem reinício solicitado não abre outro renderizador');
console.log('Renderer lifecycle: serialized restart, stale callback and stop passed.');
