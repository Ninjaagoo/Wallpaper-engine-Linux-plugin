# Wallpaper Engine Linux

**Seus wallpapers da Steam na área de trabalho do Linux.**

Integração comunitária desenvolvida e adaptada por **ninjaagoo**, com base em projetos de código aberto. Permite escolher cenas e vídeos no aplicativo oficial do Wallpaper Engine e aplicar a seleção no Linux, com integração ao desktop, cores do sistema e personalização da tela de login do GNOME.

**Ambiente validado:** Bazzite com GNOME 50, Wayland e GPU Intel. O suporte adicional ao KDE é experimental; no XFCE, a integração aplica somente uma imagem estática.

[Funcionalidades](#funcionalidades) · [Instalação](#instalação) · [Como usar](#como-usar) · [Tela de login — GDM](#tela-de-login--gdm) · [Compatibilidade](#compatibilidade) · [Créditos](#desenvolvimento-e-créditos)

## Funcionalidades

| Recurso | O que faz |
|---|---|
| Seleção imediata | Aplica o wallpaper assim que você o seleciona na biblioteca oficial, antes de pressionar **OK**. |
| Cenas e vídeos | Reconhece conteúdo desses tipos baixado da Workshop. |
| Desktop e pesquisa GNOME | Exibe a animação na área de trabalho e na visão geral/pesquisa do GNOME. |
| Cores combinando | No GNOME, escolhe uma cor de destaque a partir da prévia do wallpaper. |
| Fundos sincronizados | Atualiza os fundos estáticos dos temas claro e escuro e o fundo de bloqueio do GNOME, evitando a imagem antiga nas transições. |
| Tela de login | Com a integração opcional do GDM instalada, usa a prévia estática selecionada e acompanha as próximas trocas. |
| Início automático opcional | Ao final da instalação, pergunta se a integração deve iniciar ao entrar na sessão. |
| Qualidade e reprodução | No GNOME, oferece ajustes de FPS, áudio, monitor e enquadramento; o lançador considera a resolução física do monitor. |
| Convivência com aplicativos | Inclui adaptações de foco e posicionamento para que a janela do renderizador não interfira na minimização dos aplicativos. |
| Instalação acompanhada | Mostra as etapas, porcentagens coloridas e a confirmação de conclusão. |
| Executável offline | Reúne fontes, renderizador compilado e imagem de dependências em um arquivo `.run` para Linux x86_64. |
| Descoberta da Steam | Reconhece instalações tradicionais, Flatpak e bibliotecas adicionais declaradas em `libraryfolders.vdf`. |

O aplicativo oficial continua sendo usado para escolher wallpapers. Esta integração não substitui a instalação do Wallpaper Engine na Steam.

## Tecnologias e linguagens

| Linguagem ou tecnologia | Uso no projeto |
|---|---|
| **Python 3** | Instalador, detecção do desktop, sincronização da seleção, tratamento de imagens, inicialização e testes. |
| **JavaScript / GJS** | Extensões e preferências do GNOME, integração com o GDM e comunicação com a interface oficial. |
| **C++20** | Renderizador `linux-wallpaperengine`, com adaptações locais de comportamento da janela. |
| **Bash** | Cabeçalho do instalador executável e preparação da extração do pacote. |
| **QML** | Addon de terceiros usado na integração experimental com KDE Plasma 6. |
| **XML e JSON** | Esquemas GSettings, protocolos, metadados e configurações. |
| **Podman e Containerfile** | Compilação e execução do renderizador com dependências isoladas. |
| **GSettings, D-Bus e systemd de usuário** | Preferências, comunicação com o desktop e gerenciamento do serviço. |
| **Pillow, PyGObject e Node.js** | Processamento da prévia, acesso às APIs GNOME e validação do JavaScript da interface. |

## Compatibilidade

| Ambiente | Resultado disponível | Validação |
|---|---|---|
| GNOME 50 / Wayland | Wallpaper animado, seleção imediata, cores e fundos sincronizados | Testado no Bazzite deste computador |
| GNOME 45–49 | Extensão declara suporte a essas versões | Não testado localmente |
| KDE Plasma 6 com addon | Animação via Application Wallpaper e `xwayland-run` | Experimental; falta validação visual |
| KDE sem addon | Prévia estática sincronizada | Falta validação visual |
| XFCE | **Somente prévia estática sincronizada** | Falta validação visual |
| Outros desktops ou versões GNOME fora da faixa declarada | Não suportados | Instalador informa a incompatibilidade |

A sincronização de cores, do fundo de bloqueio e a extensão de login GDM são específicas do GNOME. Não há integração equivalente de login para SDDM ou LightDM.

Os testes automatizados verificam caminhos e comandos dos adaptadores; não comprovam o resultado visual em KDE ou XFCE. **Não há garantia de funcionamento em qualquer distribuição Linux.** Outras GPUs, drivers e arquiteturas precisam de validação.

## Requisitos

- **Steam e Wallpaper Engine** instalados, com os wallpapers da Workshop baixados.
- **Python 3 com Pillow** e **Node.js**.
- **GNOME:** PyGObject, `gnome-shell`, `gnome-extensions`, `gsettings` e `glib-compile-schemas`.
- **KDE:** `qdbus6`, `qdbus` ou `gdbus`. Para animação experimental: Plasma 6, `kpackagetool6`, `xwayland-run`, QtWayland.Compositor e plasma5support QML.
- **XFCE:** `xfconf-query` e xfdesktop em execução.
- **Renderização:** Podman com o runtime e a imagem de dependências, ou um renderizador nativo compatível. O pacote `.run` já inclui o runtime e a imagem, mas exige Podman instalado.

O instalador informa dependências ausentes e não executa `apt`, `dnf` ou `pacman` no hospedeiro. Instale os requisitos com o gerenciador da sua distribuição.

## Instalação

O instalador do usuário é **`wallpaper-linux/install.py`**. O executável `.run` prepara o runtime e chama esse mesmo instalador, utilizando as mesmas opções e validações. Você não precisa executar vários instaladores.

Internamente, a sincronização foi separada em conexão da interface oficial, cópia dos scripts e instalação do serviço. O runtime é copiado para uma pasta temporária antes da troca, preservando a versão anterior e os arquivos que um renderizador em execução ainda utiliza. Se a troca falhar, o instalador tenta restaurar a versão anterior.

O GDM continua como auxiliar interno separado por exigir privilégios de administrador, mas é acionado pela opção `--login-background` do instalador principal. O antigo `wallpaper-linux/login-screen/install.py` foi substituído por `wallpaper-linux/installation/gdm.py`; não execute esse auxiliar diretamente.

### Instalação por download do GitHub

O instalador `.run` e sua soma SHA-256 são distribuídos em [Releases](https://github.com/Ninjaagoo/Wallpaper-engine-Linux-plugin/releases), fora do histórico do repositório. Com `curl` e `sha256sum` instalados, copie este comando completo para baixar, conferir a integridade e iniciar a instalação:

```bash
diretorio_we="${XDG_CACHE_HOME:-$HOME/.cache}/wallpaper-engine/download" && mkdir -p "$diretorio_we" && curl -fL https://github.com/Ninjaagoo/Wallpaper-engine-Linux-plugin/releases/latest/download/WallpaperEngine-Linux-x86_64.run -o "$diretorio_we/WallpaperEngine-Linux-x86_64.run" && curl -fL https://github.com/Ninjaagoo/Wallpaper-engine-Linux-plugin/releases/latest/download/WallpaperEngine-Linux-x86_64.run.sha256 -o "$diretorio_we/WallpaperEngine-Linux-x86_64.run.sha256" && (cd "$diretorio_we" && sha256sum -c WallpaperEngine-Linux-x86_64.run.sha256 && bash ./WallpaperEngine-Linux-x86_64.run)
```

Execute com seu usuário normal, sem `sudo`. Steam, Wallpaper Engine e as dependências do hospedeiro continuam sendo necessários. A opção de início automático será perguntada ao final da instalação.

### Executável pronto: um único comando

Na pasta do projeto:

```bash
chmod +x dist/WallpaperEngine-Linux-x86_64.run && ./dist/WallpaperEngine-Linux-x86_64.run
```

Se você baixou apenas o arquivo `.run`, execute na pasta em que ele está:

```bash
chmod +x WallpaperEngine-Linux-x86_64.run && ./WallpaperEngine-Linux-x86_64.run
```

Execute com seu usuário normal, **sem `sudo`**. Quando disponível, também é possível escolher **Executar como programa** no gerenciador de arquivos; o instalador tenta abrir um terminal.

O pacote é destinado a **Linux x86_64**. Não é um AppImage independente das ferramentas do hospedeiro. Inclui componentes de vários GB e extrai os arquivos em `~/.cache/wallpaper-engine/installers`, com limpeza temporária ao encerrar normalmente.

Para verificar a integridade ou os requisitos sem instalar, usando o arquivo dentro do projeto:

```bash
./dist/WallpaperEngine-Linux-x86_64.run --verify
./dist/WallpaperEngine-Linux-x86_64.run --check
```

### Instalação pelos scripts

Na pasta do projeto:

```bash
python3 wallpaper-linux/install.py --check
python3 wallpaper-linux/install.py
```

Esse caminho exige um renderizador já preparado ou uma das opções de compilação/renderizador nativo explicadas em [Opções avançadas](#opções-avançadas).

### Progresso colorido

| Porcentagem | Cor |
|---|---|
| 0–49% | Vermelho |
| 50–79% | Laranja |
| 80–100% | Verde |

As porcentagens acompanham etapas concluídas, não o tempo restante. Compilações e cópias grandes podem permanecer na mesma porcentagem enquanto trabalham. Ao finalizar com sucesso, aparece **“Concluído!”**.

As cores são ativadas automaticamente no terminal. As opções `--color always` e `--color never` forçam ou desativam as cores:

```bash
python3 wallpaper-linux/install.py --color always
python3 wallpaper-linux/install.py --color never
```

### Escolher o início automático

Ao final da instalação, o terminal pergunta:

```text
Deseja que o Wallpaper Engine inicie junto com o sistema? [s/n]:
```

- **s:** ativa o início automático ao entrar na sessão gráfica.
- **n:** desativa o início automático; você pode abrir **Wallpaper Engine Linux** pelo menu quando desejar.

A escolha controla o serviço, o autostart XDG e o comportamento da extensão GNOME. Para alterar a preferência, execute o instalador novamente. Em instalações sem interação, informe a escolha explicitamente:

```bash
python3 wallpaper-linux/install.py --startup yes
python3 wallpaper-linux/install.py --startup no
```

As opções `--startup`, `--color`, `--desktop`, `--steam-root`, `--kde-plugin` e `--login-background` também estão disponíveis no `.run`.

## Como usar

1. Abra o Wallpaper Engine pela Steam.
2. Assine os wallpapers desejados na Workshop e aguarde o download.
3. Selecione uma **cena ou vídeo** na biblioteca, sem precisar pressionar **OK** para aplicar a seleção no Linux.
4. No GNOME, abra **Wallpaper Engine Linux** no menu para ajustar FPS, áudio, monitor ou enquadramento.

Também é possível abrir as preferências com:

```bash
gnome-extensions prefs wallpaperengine@waylandwe
```

Com o início automático ativado, não é necessário abrir o aplicativo oficial em cada inicialização. A integração utiliza a última configuração ou seleção registrada. O autostart XDG permite iniciar a integração em sessões sem systemd de usuário.

A instalação preserva o wallpaper, o FPS e o volume já configurados. A resolução física foi ajustada para **1920×1080 e 60 FPS neste computador**; isso não representa uma configuração universal. Resolução e FPS maiores aumentam o consumo de GPU, e a nitidez depende também do conteúdo original.

## Tela de login — GDM

A tela de login é a tela exibida **antes de entrar na sua conta**. A integração opcional do GDM utiliza uma **imagem estática da prévia do wallpaper selecionado**, enquanto a animação continua sendo aplicada na área de trabalho após o login.

| Função | Comportamento |
|---|---|
| Aplicar a seleção atual | Usa a prévia da última seleção registrada; se não houver registro, consulta a configuração da extensão GNOME. |
| Acompanhar novas seleções | O sincronizador atualiza a imagem compartilhada quando você seleciona outro wallpaper compatível. |
| Atualizar o fundo do GDM | A extensão acompanha alterações na pasta da imagem e recria os fundos dos monitores. |
| Adaptar aos monitores | Cria um fundo por monitor, preenchendo a área com recorte proporcional da imagem. |
| Preservar a configuração anterior | O instalador mantém um backup da extensão e da configuração GDM anteriores em `/var/lib/firewatch-login-backup`. |
| Separar imagem e código | A extensão permanece protegida pelo administrador; somente a pasta da imagem fica gravável pelo usuário configurado. |
| Evitar interromper a sessão | O instalador não reinicia o GDM nem encerra sua sessão. |

Para configurar:

```bash
python3 wallpaper-linux/install.py --login-background
```

Será solicitada autenticação de administrador para instalar a extensão e configurar o GDM. Depois da preparação inicial, as próximas trocas da imagem não exigem nova senha. Se a extensão de login deste projeto já estiver instalada, o instalador principal atualiza essa configuração automaticamente.

A imagem compartilhada fica em `/var/lib/wallpaper-engine-login/background.png`. A configuração do GDM é compartilhada pelo computador e acompanha o usuário que a preparou; não há seleção independente por conta nesta implementação.

**Para carregar a extensão instalada ou atualizada, salve seu trabalho e reinicie o computador.** A imagem já configurada acompanha seleções posteriores pelo sincronizador. Esta função foi preparada para GNOME com GDM; não altera o logotipo Acer do firmware, o menu de boot ou a animação de inicialização do sistema.

## Opções avançadas

### Compilar o renderizador

O renderizador é mantido como submódulo do projeto original. Para baixar os fontes com as dependências:

```bash
git clone --recurse-submodules https://github.com/Ninjaagoo/Wallpaper-engine-Linux-plugin.git
cd Wallpaper-engine-Linux-plugin
```

Se já clonou sem os submódulos, inicialize as dependências:

```bash
git submodule update --init --recursive
```

As alterações locais estão em `patches/linux-wallpaperengine-background.patch`. O instalador aplica o patch antes da compilação e reconhece quando ele já foi aplicado.

Com Podman e Git disponíveis:

```bash
python3 wallpaper-linux/install.py --build-runtime
```

A opção baixa dependências e CEF e compila o código local usando o `Containerfile`. Pode exigir vários GB de espaço e levar vários minutos. A imagem utiliza Fedora para isolar bibliotecas do hospedeiro. Uma reconstrução completa não foi repetida durante a reorganização desta documentação.

### Usar um renderizador nativo

```bash
python3 wallpaper-linux/install.py --renderer /usr/local/bin/linux-wallpaperengine
```

Nesse modo, as bibliotecas nativas e o mpv precisam estar disponíveis no hospedeiro. Os controles adicionais de foco dependem das adaptações incluídas neste projeto; um binário externo pode não conter essas alterações.

### Informar o ambiente e o caminho da Steam

```bash
python3 wallpaper-linux/install.py --desktop gnome
python3 wallpaper-linux/install.py --desktop kde --steam-root "/caminho/Steam"
python3 wallpaper-linux/install.py --desktop xfce
```

O caminho informado em `--steam-root` deve conter a pasta `steamapps`.

### Ativar o addon experimental do KDE Plasma 6

```bash
python3 wallpaper-linux/install.py --desktop kde --kde-plugin
```

As dependências QML e `xwayland-run` devem estar instaladas antes. Sem o addon disponível, o KDE utiliza a prévia estática. Para esse backend, `~/.config/wallpaper-engine/config.json` aceita `fps` e `render_size`, por exemplo:

```json
{
  "fps": 60,
  "render_size": [1920, 1080]
}
```

Esses campos complementam a configuração existente; preserve as outras chaves do arquivo.

### Gerar o executável

Com o runtime e a imagem Podman preparados neste computador:

```bash
python3 tools/build-release.py
```

O gerador cria o `.run` e o arquivo `.run.sha256` em `dist/`. O SHA-256 permite conferir se o pacote corresponde ao arquivo distribuído.

## Como a integração funciona

```text
Wallpaper Engine na Steam
          │ seleção de uma cena ou vídeo
          ▼
Serviço local de sincronização
          ├── GNOME: extensão animada, destaque e fundos estáticos
          ├── GDM configurado: prévia estática da tela de login
          ├── KDE: addon experimental ou prévia estática
          └── XFCE: prévia estática
```

A interface envia a seleção para `127.0.0.1:49367`, com um token de autenticação. O serviço valida o caminho da Workshop e aplica a seleção no adaptador do desktop.

No GNOME, a extensão posiciona cópias da imagem renderizada nos fundos do desktop e da visão geral. No modo em contêiner, o renderizador utiliza XWayland, sem rede, com as bibliotecas Steam montadas somente para leitura. Também existe o modo de execução nativa.

Os componentes instalados ficam fora da pasta do projeto. Mover os fontes em `Documentos` não interrompe a integração instalada.

## Organização dos arquivos

| Caminho | Responsabilidade |
|---|---|
| `wallpaper-linux/install.py` | Única entrada de instalação para o usuário; coordena as etapas e a escolha do início automático |
| `wallpaper-linux/installation/options.py` | Opções compartilhadas pelo instalador normal e offline |
| `wallpaper-linux/installation/requirements.py` | Validação de dependências e versões GNOME |
| `wallpaper-linux/installation/runtime.py` | Compilação, importação e troca segura do renderizador |
| `wallpaper-linux/installation/offline.py` | Prepara o pacote extraído e chama o instalador principal |
| `wallpaper-linux/installation/gdm.py` | Auxiliar interno de administrador para imagem, backup e extensão GDM |
| `wallpaper-linux/install_progress.py` | Progresso e cores do instalador |
| `wallpaper-linux/desktop_support.py` | Detecção do desktop, caminhos Steam e adaptadores KDE/XFCE |
| `wallpaper-linux/selection-sync.py` | Seleção imediata, cores e atualização das imagens de fundo |
| `wallpaper-linux/session-start.py` | Inicialização da integração e abertura pelo menu |
| `wallpaper-linux/wallpaper-renderer` | Lançador do renderizador nativo ou em contêiner |
| `wallpaper-linux/extension/` | Extensão GNOME e preferências adaptadas |
| `wallpaper-linux/login-screen/` | Arquivos e imagem de referência da extensão GDM; sem instalador separado |
| `wallpaper-linux/tests/` | Testes automatizados |
| `wallpaper-linux/vendor/` | Addon KDE de terceiros, com licença original |
| `linux-wallpaperengine/` | Submódulo do renderizador C++ e suas dependências |
| `patches/` | Alterações locais reproduzíveis sobre o renderizador original |
| `tools/build-release.py` | Exporta dependências, compacta arquivos, gera o executável e calcula o SHA-256 |
| `tools/package-bootstrap.py` | Pequena entrada interna do `.run`, que delega ao módulo offline |
| `dist/` | Executável e soma SHA-256 |
| `.vscode/` | Configuração do editor e IntelliSense |

### Arquivos instalados no usuário

| Caminho | Conteúdo |
|---|---|
| `~/.local/share/wallpaper-engine/` | Renderizador e integração instalados; mantenha esta pasta |
| `~/.config/wallpaper-engine/config.json` | Preferências da integração e início automático |
| `~/.local/state/wallpaper-engine/last-selection.json` | Última seleção aplicada |
| `~/.local/state/wallpaper-engine/wallpaper-ui-original.js` | Backup da interface oficial |
| `~/.config/autostart/wallpaper-engine-linux.desktop` | Entrada de início automático, quando ativada |
| `~/.config/systemd/user/wallpaper-selection-sync.service` | Serviço de sincronização |
| `~/.local/bin/wallpaper-engine-start` | Comando para iniciar a integração |

Somente os nomes das variáveis do código próprio foram padronizados em português, sem acentos nos identificadores. Contadores usam `i` e `j`; sintaxe, APIs, funções, métodos, opções de terminal e chaves de configuração podem permanecer em inglês. O código dos componentes externos conserva seus nomes originais.

## Diagnóstico e atualização

Verificar o serviço e a extensão GNOME:

```bash
systemctl --user status wallpaper-selection-sync.service
gnome-extensions info wallpaperengine@waylandwe
```

Consultar os logs e reiniciar a sincronização:

```bash
journalctl --user -u wallpaper-selection-sync.service -n 50 --no-pager
tail -n 50 ~/.local/state/wallpaper-engine/renderer.log
systemctl --user restart wallpaper-selection-sync.service
```

Em sessões sem systemd de usuário, consulte `~/.local/state/wallpaper-engine/selection-sync.log`. Para iniciar manualmente:

```bash
~/.local/bin/wallpaper-engine-start
```

| Situação | O que fazer |
|---|---|
| Seleção não chega ao Linux | Feche e reabra o Wallpaper Engine. |
| Atualização oficial removeu a integração da interface | Execute novamente o instalador. |
| Extensão GNOME foi atualizada | Salve seu trabalho, saia e entre na sessão para carregar o código novo. |
| GDM ainda mostra a imagem antiga | Confirme a configuração com `--login-background` e reinicie o computador para carregar a extensão atualizada. |
| KDE ou XFCE mostra uma imagem sem animação | Confira o estado de suporte na tabela de compatibilidade. |
| Erros de inclusão no VS Code | Confira `.vscode/c_cpp_properties.json` e execute **C/C++: Reset IntelliSense Database**. |

Os cabeçalhos usados pelo IntelliSense ficam em `~/.cache/wallpaper-engine/intellisense`, separados do runtime. A pasta de compilação C++ removida durante a limpeza precisa ser gerada novamente para uma recompilação nativa.

## Testes

Na pasta do projeto:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s wallpaper-linux/tests -v
```

A suíte de instalação verifica opções compartilhadas, dependências e versões incompatíveis, encaminhamento das opções e do ambiente ao instalador principal, `--check` sem instalação, chamadas GSettings, restrição do auxiliar GDM e substituição do runtime sem invalidar arquivos em uso. Os testes não alteram a sessão real nem substituem a validação visual dos desktops.

## Desenvolvimento e créditos

**Desenvolvedor da integração e das adaptações locais: ninjaagoo.**

O projeto reúne código existente, modificações locais e scripts de integração. Agradecimentos aos autores e colaboradores que disponibilizaram as bases utilizadas:

| Projeto e autoria | Contribuição utilizada |
|---|---|
| [linux-wallpaperengine — Almamu e colaboradores](https://github.com/Almamu/linux-wallpaperengine) | Renderizador de wallpapers no Linux; fonte em `linux-wallpaperengine/`. |
| [Wallpaper Engine for Wayland — diaslucass e colaboradores](https://github.com/diaslucass/wallpaperEngineWayland) | Base da extensão GNOME, adaptada em `wallpaper-linux/extension/`. |
| [Application Wallpaper for Plasma 6 — Sebastian Krzyszkowiak e colaboradores](https://invent.kde.org/dos/plasma-wallpaper-application) | Addon da integração experimental com KDE, preservado em `wallpaper-linux/vendor/plasma-application/`. |

As adaptações locais incluem sincronização imediata da seleção, cores do GNOME, fundos estáticos e GDM, integração com a visão geral, ajustes de foco e minimização, resolução física, execução isolada, início automático opcional, instalador unificado e empacotamento executável.

Os créditos reconhecem o código utilizado; não indicam participação direta, parceria ou endosso dos autores originais a esta adaptação. As alterações locais não foram incorporadas aos repositórios originais.

### Licenças e autoria

Mantenha os avisos de autoria e consulte as licenças de cada componente antes de redistribuir o projeto. O addon KDE utiliza **GPL-3.0-or-later**; a cópia incluída corresponde ao commit `eea391bb50e9e933e0f601dd432684bc0f9176e7`. As demais bases e dependências mantêm seus respectivos avisos. O repositório `diaslucass/wallpaperEngineWayland` não declara uma licença na versão consultada; os créditos não representam uma autorização de redistribuição. Não foi atribuída uma licença nova ao código desse componente.
