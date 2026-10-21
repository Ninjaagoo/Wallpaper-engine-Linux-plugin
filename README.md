# Wallpaper Engine Linux

**Wallpapers da Steam na área de trabalho do Linux — projeto experimental.**

Integração comunitária desenvolvida e adaptada por **ninjaagoo**, a partir de projetos de código aberto. Usa o aplicativo oficial do Wallpaper Engine para selecionar cenas e vídeos e aplica a seleção no desktop Linux.

> **Em desenvolvimento:** não é um produto oficial do Wallpaper Engine e ainda não reproduz todos os recursos do motor original. Algumas cenas podem apresentar partes ausentes, cores incorretas, efeitos diferentes ou modelos deformados. Compilar os shaders sem erros não garante fidelidade visual.

O ambiente testado é **Bazzite, GNOME 50, Wayland e GPU Intel**. Consulte a tabela de [Compatibilidade](#compatibilidade) para os demais ambientes.

[Instalar](#instalação) · [Como usar](#como-usar) · [Compatibilidade](#compatibilidade) · [Diagnóstico](#diagnóstico-e-atualização) · [Créditos](#desenvolvimento-e-créditos)

## Exemplos visuais

| Captura de teste local | Exemplo do motor original |
|---|---|
| ![Dark Queen renderizado em teste local 4K](docs/media/dark-queen-4k.png) | ![Cena de NieR Automata demonstrada pelo motor original](docs/media/wallpaper-exemplo.png) |
| **Dark Queen [4K]** — captura do renderizador local em 3840 × 2160, usando Xvfb/Mesa. | **NieR Automata** — quadro da demonstração publicada pelo projeto base. |

### Wallpaper em animação

![Demonstração animada de uma cena no linux-wallpaperengine](docs/media/wallpaper-animado.gif)

O GIF e o quadro de NieR Automata vêm de [Almamu/linux-wallpaperengine](https://github.com/Almamu/linux-wallpaperengine/tree/b016d7d1fdcf4e5fd2f9c9fa420a8aaa07fee02d/docs/images). São demonstrações do motor original, não gravações desta integração no GNOME. A captura local documenta um teste específico; não garante compatibilidade com todos os wallpapers. As imagens pertencem aos respectivos autores.

## Instalação

### 1. Antes de começar

Você precisa ter:

- **Linux x86_64** e um [desktop compatível](#compatibilidade).
- **Steam e Wallpaper Engine instalados pela sua conta**, com pelo menos uma cena ou vídeo da Workshop já baixado. O plugin não inclui o aplicativo pago nem os wallpapers.
- **Bash, `curl`, `tar`, `sha256sum`, `awk` e `mktemp`** disponíveis para executar o comando de download.
- Conexão com a internet e espaço para baixar e extrair **vários GB** de runtime e dependências.
- Acesso a **`sudo`**, caso faltem pacotes do sistema.

O instalador tenta instalar Python 3, Pillow, Node.js, Podman e as ferramentas necessárias ao desktop quando ausentes. Os gerenciadores previstos são `apt-get`, `dnf`, `pacman` e `rpm-ostree`; a instalação real em todas essas distribuições ainda não foi validada. Outros sistemas podem exigir preparação manual.

### 2. Execute este comando

Copie a linha inteira no terminal, usando seu usuário normal, **sem colocar `sudo` no início**:

```bash
arquivo_we=$(mktemp) && curl -fL https://raw.githubusercontent.com/Ninjaagoo/Wallpaper-engine-Linux-plugin/v0.2.2-rc.1/install.sh -o "$arquivo_we" && bash "$arquivo_we"; resultado_we=$?; [ -z "${arquivo_we:-}" ] || rm -f "$arquivo_we"; (exit "$resultado_we")
```

Esse comando instala a pré-lançamento experimental **v0.2.2-rc.1**: baixa o pacote, confere o SHA-256, prepara as dependências e instala a integração. Ele inclui as adaptações atuais de shaders, composição e troca de wallpaper, ainda sujeitas às limitações descritas acima.

Se necessário, o instalador solicita autenticação de administrador e reutiliza a autorização durante a execução. As etapas mostram porcentagens: vermelho no início, laranja de 50–79% e verde de 80–100%. Elas representam etapas concluídas, não tempo restante.

**No Bazzite e em outros sistemas `rpm-ostree`:** se forem adicionados pacotes ao sistema, reinicie e execute o mesmo comando para concluir. O instalador avisa e não reinicia o computador sozinho.

### 3. Conclua e escolha seu wallpaper

1. Ao aparecer **“Deseja que o Wallpaper Engine inicie junto com o sistema?”**, responda `s` para iniciar ao entrar na sessão ou `n` para abrir manualmente pelo menu.
2. Aguarde a mensagem **“Concluído!”**. Se o instalador informar um erro, consulte [Diagnóstico](#diagnóstico-e-atualização).
3. No GNOME, salve seu trabalho, saia da conta e entre novamente para carregar a extensão instalada ou atualizada.
4. Siga os passos de [Como usar](#como-usar) para selecionar o wallpaper.

A integração fica na pasta oculta **`~/.local/share/wallpaper-engine/`** e funciona independentemente da pasta do projeto. Consulte [Diagnóstico](#diagnóstico-e-atualização) para localizar os logs.

### Alternativa: baixar o executável manualmente

Baixe o arquivo **`WallpaperEngine-Linux-x86_64.run`** em [Releases](https://github.com/Ninjaagoo/Wallpaper-engine-Linux-plugin/releases). Na pasta onde ele foi salvo:

```bash
bash WallpaperEngine-Linux-x86_64.run --install-deps
```

Esse é o mesmo fluxo de instalação, sem precisar clonar ou compilar o projeto. O pacote inclui o renderizador e a imagem de dependências; **não é um AppImage autossuficiente** e utiliza Podman no hospedeiro.

Para conferir o pacote ou verificar o ambiente sem instalar:

```bash
bash WallpaperEngine-Linux-x86_64.run --verify
bash WallpaperEngine-Linux-x86_64.run --check
```

Para compilar ou instalar pelos fontes, consulte [Opções avançadas](#opções-avançadas).

## Como usar

1. Abra o Wallpaper Engine pela Steam e aguarde o download dos wallpapers da Workshop.
2. Selecione uma **cena ou vídeo** na biblioteca. A integração aplica a seleção antes de pressionar **OK**.
3. No GNOME, abra **Wallpaper Engine Linux** pelo menu para ajustar FPS, áudio, monitor e enquadramento.

Com o início automático ativado, a última seleção é carregada ao entrar na sessão, sem precisar abrir o aplicativo oficial novamente.

Para cenas, comece com **30 FPS** para reduzir o consumo. Vídeos preservam sua taxa de quadros original. A saída acompanha a resolução física do monitor; usar conteúdo 4K não elimina as limitações do motor nem aumenta a resolução da tela.

As preferências existentes são preservadas na reinstalação. O padrão para novas instalações é 30 FPS.

## Compatibilidade

| Ambiente | Resultado disponível | Validação |
|---|---|---|
| GNOME 50 / Wayland | Wallpaper animado, seleção imediata, cores e fundos sincronizados | Testado no Bazzite |
| GNOME 45–49 | Extensão declara suporte a essas versões | Não testado localmente |
| KDE Plasma 6 com addon | Animação via Application Wallpaper e `xwayland-run` | Experimental; falta validação visual |
| KDE sem addon | Prévia estática sincronizada | Falta validação visual |
| XFCE | **Somente prévia estática sincronizada** | Falta validação visual |
| Outros desktops ou versões GNOME fora da faixa declarada | Não suportados | Instalador informa a incompatibilidade |

A sincronização de cores, do fundo de bloqueio e a extensão de login GDM são específicas do GNOME. Não há integração equivalente de login para SDDM ou LightDM.

**Não há garantia de funcionamento em qualquer distribuição Linux.** Outras GPUs, drivers e arquiteturas precisam de validação; o alcance dos testes está descrito em [Testes](#testes).

## Funcionalidades

- Seleção imediata de cenas e vídeos pela interface oficial.
- Animação no desktop e na visão geral do GNOME.
- Cor de destaque e fundos estáticos sincronizados no GNOME.
- Início automático opcional ao entrar na sessão.
- Ajustes de FPS, áudio, monitor e enquadramento no GNOME.
- Detecção de bibliotecas Steam tradicionais e Flatpak.
- Prévia estática opcional na tela de login GDM.

## Tela de login — GDM

No GNOME com GDM, é possível usar a **prévia estática** do wallpaper selecionado na tela de login. Essa opção exige autenticação de administrador e altera uma configuração compartilhada pelo computador.

Ao executar o arquivo baixado, acrescente:

```bash
bash WallpaperEngine-Linux-x86_64.run --install-deps --login-background
```

Depois da instalação, salve seu trabalho e reinicie o computador para carregar a extensão do GDM. As próximas seleções atualizam a imagem sem nova senha. A função não modifica o logotipo do fabricante nem a animação de boot.

## Opções avançadas

Para trabalhar com os fontes:

```bash
git clone --recurse-submodules https://github.com/Ninjaagoo/Wallpaper-engine-Linux-plugin.git
cd Wallpaper-engine-Linux-plugin
python3 wallpaper-linux/install.py --check
python3 wallpaper-linux/install.py --install-deps --build-runtime
```

A compilação exige Git, Podman, internet e vários GB livres. Pode levar vários minutos. As adaptações do motor são aplicadas a partir de `patches/*.patch`.

| Opção | Uso |
|---|---|
| `--startup yes` / `--startup no` | Define o início automático sem pergunta interativa. |
| `--desktop gnome`, `kde` ou `xfce` | Informa o ambiente manualmente. |
| `--steam-root /caminho/Steam` | Informa a pasta que contém `steamapps`. |
| `--kde-plugin` | Instala o addon experimental do Plasma 6. |
| `--login-background` | Configura a prévia estática no GDM. |
| `--renderer /caminho/linux-wallpaperengine` | Usa um renderizador nativo, com bibliotecas e codecs instalados no hospedeiro. |

As opções `--build-runtime` e `--renderer` são específicas do instalador pelos fontes. As demais também são aceitas pelo `.run`. Consulte `--help` para todas as opções.

## Diagnóstico e atualização

Os arquivos principais ficam em `~/.local/share/wallpaper-engine/`. Use **Ctrl+H** no gerenciador de arquivos para exibir pastas ocultas. A extensão, o serviço e os atalhos usam os locais próprios do desktop; o Podman mantém as imagens no seu armazenamento.

Para consultar o serviço e os logs em sessões com systemd:

```bash
systemctl --user status wallpaper-selection-sync.service
journalctl --user -u wallpaper-selection-sync.service -n 50 --no-pager
tail -n 50 ~/.local/share/wallpaper-engine/state/renderer.log
```

Sem systemd de usuário, consulte `~/.local/share/wallpaper-engine/state/selection-sync.log`.

| Problema | O que fazer |
|---|---|
| A seleção não chega ao Linux | Feche e reabra o Wallpaper Engine. |
| Uma atualização oficial removeu a integração | Execute novamente o instalador. |
| A extensão GNOME foi atualizada | Saia e entre na sessão para carregar o código novo. |
| Consumo ou aquecimento elevado | Reduza o FPS nas preferências e verifique o consumo dos outros aplicativos. |
| Partes ausentes, cores ou efeitos incorretos | Pode ser uma limitação do motor experimental; informe o wallpaper, o desktop, a GPU e o log. |
| KDE ou XFCE sem animação | Confira a tabela de compatibilidade. |

Para iniciar manualmente, execute `~/.local/bin/wallpaper-engine-start`. Para reiniciar a sincronização em sessões com systemd, use `systemctl --user restart wallpaper-selection-sync.service`.

## Tecnologias e linguagens

<p>
  <img src="https://img.shields.io/badge/Python_3-111111?style=flat-square&amp;logo=python&amp;logoColor=3776AB" alt="Python 3" height="40">
  <img src="https://img.shields.io/badge/JavaScript_GJS-111111?style=flat-square&amp;logo=javascript&amp;logoColor=F7DF1E" alt="JavaScript/GJS" height="40">
  <img src="https://img.shields.io/badge/C%2B%2B20-111111?style=flat-square&amp;logo=cplusplus&amp;logoColor=00599C" alt="C++20" height="40">
  <img src="https://img.shields.io/badge/Bash-111111?style=flat-square&amp;logo=gnubash&amp;logoColor=4EAA25" alt="Bash" height="40">
  <img src="https://img.shields.io/badge/QML-111111?style=flat-square&amp;logo=qt&amp;logoColor=41CD52" alt="QML / Qt" height="40">
  <img src="https://img.shields.io/badge/XML-111111?style=flat-square&amp;logo=xml&amp;logoColor=F16529" alt="XML" height="40">
  <img src="https://img.shields.io/badge/JSON-111111?style=flat-square&amp;logo=json&amp;logoColor=FFFFFF" alt="JSON" height="40">
</p>

A integração utiliza Linux, Podman, GSettings, D-Bus e systemd de usuário.

## Testes

As mudanças são testadas localmente antes de preparar uma versão. Os testes automatizados verificam a integração e partes do renderizador; não substituem a validação visual dos wallpapers e desktops.

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s wallpaper-linux/tests -v
node tools/test-renderer-lifecycle.mjs
```

O teste C++ em `tools/test-native-rendering.cpp` verifica parsing, shaders e composição; a opção `--opengl` exige um display OpenGL. Os executáveis distribuídos só recebem as mudanças quando uma nova versão é preparada e publicada.

## Desenvolvimento e créditos

<table>
  <tr>
    <td><a href="https://github.com/Ninjaagoo"><img src="docs/media/ninjaagoo.png" width="80" height="80" alt="Foto de perfil de Ninjaagoo no GitHub"></a></td>
    <td><strong><a href="https://github.com/Ninjaagoo">Ninjaagoo</a></strong><br>Desenvolvedor da integração e das adaptações locais.</td>
  </tr>
</table>

O projeto reúne código existente, modificações locais e scripts de integração. Agradecimentos aos autores e colaboradores que disponibilizaram as bases utilizadas:

| Projeto e autoria | Contribuição utilizada |
|---|---|
| [linux-wallpaperengine — Almamu e colaboradores](https://github.com/Almamu/linux-wallpaperengine) | Renderizador de wallpapers no Linux; fonte em `linux-wallpaperengine/`. |
| [Wallpaper Engine for Wayland — diaslucass e colaboradores](https://github.com/diaslucass/wallpaperEngineWayland) | Base da extensão GNOME, adaptada em `wallpaper-linux/extension/`. |
| [Application Wallpaper for Plasma 6 — Sebastian Krzyszkowiak e colaboradores](https://invent.kde.org/dos/plasma-wallpaper-application) | Addon da integração experimental com KDE, preservado em `wallpaper-linux/vendor/plasma-application/`. |

Os créditos reconhecem o código utilizado; não indicam participação direta, parceria ou endosso dos autores originais a esta adaptação. As alterações locais não foram incorporadas aos repositórios originais.

### Licenças e autoria

Mantenha os avisos de autoria e consulte as licenças de cada componente antes de redistribuir o projeto. O addon KDE utiliza **GPL-3.0-or-later**; a cópia incluída corresponde ao commit `eea391bb50e9e933e0f601dd432684bc0f9176e7`. As demais bases e dependências mantêm seus respectivos avisos. O repositório `diaslucass/wallpaperEngineWayland` não declara uma licença na versão consultada; os créditos não representam uma autorização de redistribuição. Não foi atribuída uma licença nova ao código desse componente.
