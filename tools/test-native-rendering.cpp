// Link against the rebuilt engine library to exercise real scene parsing.
#include "WallpaperEngine/Data/Parsers/ObjectParser.h"
#include "WallpaperEngine/Data/Model/Project.h"
#include "WallpaperEngine/Data/Model/Wallpaper.h"
#include "WallpaperEngine/Render/Shaders/Compatibility.h"
#include "WallpaperEngine/Render/Shaders/GLSLContext.h"
#include "WallpaperEngine/Render/Shaders/Shader.h"
#include <iostream>

int main () {
    using WallpaperEngine::Data::JSON::JSON;
    using WallpaperEngine::Data::Model::Project;
    using WallpaperEngine::Data::Model::Text;
    using WallpaperEngine::Data::Parsers::ObjectParser;
    const Project projeto {};
    for (const auto& preenchimento : { JSON ("32.00000 16.00000"), JSON (8), JSON (nullptr) }) {
        JSON dados { { "id", 1 }, { "name", "Regression" }, { "text", "Test" },
                     { "padding", preenchimento } };
        const auto objeto = ObjectParser::parse (dados, projeto);
        const auto* texto = dynamic_cast<const Text*> (objeto.get ());
        const float horizontal = preenchimento.is_string () ? 32.0f : preenchimento.is_number () ? 8.0f : 0.0f;
        const float vertical = preenchimento.is_string () ? 16.0f : horizontal;
        if (!texto || texto->padding.x != horizontal || texto->padding.y != vertical) {
            std::cerr << "Text padding regression: " << dados.dump () << '\n';
            return 1;
        }
    }
    std::cout << "Text parser: vector, scalar and default padding passed.\n";
    using namespace WallpaperEngine::Render::Shaders;
    const std::string cabecalho = "#version 330\n";
    const std::string vertice = cabecalho + "out vec2 v_TexCoord; void main() { v_TexCoord=vec2(0.5); gl_Position=vec4(0.0); }";
    const std::string fragmento = cabecalho + "#define varying in\nvarying vec2 v_TexCoord;\nout vec4 color;\n"
        "void main() { v_TexCoord.xy += vec2(0.1); color = vec4(v_TexCoord, 0.0, 1.0); }";
    const auto fontes = GLSLContext::get ().toGlsl (vertice, writableTexCoord (fragmento));
    if (fontes.first.empty () || fontes.second.empty ()) return 2;
    const std::string somenteLeitura = "varying vec2 v_TexCoord; void main() { float x = v_TexCoord.x; }";
    if (writableTexCoord (somenteLeitura) != somenteLeitura) return 3;
    std::cout << "Shader compatibility: writable input compiles; read-only input preserved.\n";
    const WallpaperEngine::Assets::AssetLocator localizador (nullptr);
    const WallpaperEngine::Data::Model::ComboMap combinacoes;
    const WallpaperEngine::Data::Model::ShaderConstantMap constantes;
    const WallpaperEngine::Data::Model::TextureMap texturas;
    Shader copia (localizador, "commands/copy", combinacoes, combinacoes, texturas, texturas, constantes);
    const auto shadersCopia = GLSLContext::get ().toGlsl (copia.vertex (), copia.fragment ());
    if (shadersCopia.first.empty () || shadersCopia.second.empty ()) return 4;
    std::cout << "Built-in copy command: vertex and fragment shaders compile.\n";
}
