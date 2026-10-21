// Link against the rebuilt engine library to exercise real scene parsing.
#include "WallpaperEngine/Data/Parsers/ObjectParser.h"
#include "WallpaperEngine/Data/Model/Project.h"
#include "WallpaperEngine/Data/Model/Wallpaper.h"
#include "WallpaperEngine/Render/Shaders/Compatibility.h"
#include "WallpaperEngine/Render/Shaders/GLSLContext.h"
#include "WallpaperEngine/Render/Shaders/Shader.h"
#include <iostream>
#include <GL/glew.h>
#include <GLFW/glfw3.h>
#include "WallpaperEngine/Render/Helpers/Blending.h"
#include <cmath>

int main (int argc, char** argv) {
    const bool validarGPU = argc > 1 && std::string (argv[1]) == "--opengl";
    if (validarGPU) {
        if (!glfwInit ()) return 10;
        glfwWindowHint (GLFW_VISIBLE, GLFW_FALSE);
        glfwWindowHint (GLFW_CONTEXT_VERSION_MAJOR, 3);
        glfwWindowHint (GLFW_CONTEXT_VERSION_MINOR, 3);
        const auto janela = glfwCreateWindow (64, 64, "Shader tests", nullptr, nullptr);
        if (!janela) return 11;
        glfwMakeContextCurrent (janela);
        glewExperimental = true;
        if (glewInit () != GLEW_OK) return 12;
    }
    if (validarGPU) {
        GLuint textura, framebuffer, vao;
        glGenTextures (1, &textura);
        glBindTexture (GL_TEXTURE_2D, textura);
        glTexImage2D (GL_TEXTURE_2D, 0, GL_RGBA32F, 1, 1, 0, GL_RGBA, GL_FLOAT, nullptr);
        glGenFramebuffers (1, &framebuffer);
        glBindFramebuffer (GL_FRAMEBUFFER, framebuffer);
        glFramebufferTexture2D (GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, textura, 0);
        if (glCheckFramebufferStatus (GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE) return 13;
        const GLuint programa = glCreateProgram ();
        for (const auto& etapa : {
            std::pair {GL_VERTEX_SHADER, "#version 330\nvoid main(){vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);gl_Position=vec4(p*2.0-1.0,0,1);}"},
            std::pair {GL_FRAGMENT_SHADER, "#version 330\nout vec4 color;void main(){color=vec4(1,0,0,0.5);}"}
        }) {
            const GLuint shader = glCreateShader (etapa.first);
            glShaderSource (shader, 1, &etapa.second, nullptr);
            glCompileShader (shader);
            GLint sucesso = 0;
            glGetShaderiv (shader, GL_COMPILE_STATUS, &sucesso);
            if (!sucesso) return 14;
            glAttachShader (programa, shader);
            glDeleteShader (shader);
        }
        glLinkProgram (programa);
        GLint sucesso = 0;
        glGetProgramiv (programa, GL_LINK_STATUS, &sucesso);
        if (!sucesso) return 15;
        glUseProgram (programa);
        glGenVertexArrays (1, &vao);
        glBindVertexArray (vao);
        glViewport (0, 0, 1, 1);
        glClearColor (0, 0, 0, 0);
        glClear (GL_COLOR_BUFFER_BIT);
        WallpaperEngine::Render::Helpers::setupTranslucentBlending ();
        for (const float esperado : {0.5f, 0.75f}) {
            glDrawArrays (GL_TRIANGLES, 0, 3);
            float pixel[4] {};
            glReadPixels (0, 0, 1, 1, GL_RGBA, GL_FLOAT, pixel);
            if (std::abs (pixel[0] - esperado) > 0.001f || std::abs (pixel[3] - esperado) > 0.001f
                || pixel[1] != 0.0f || pixel[2] != 0.0f) {
                std::cerr << "Compositing coverage regression: " << pixel[0] << ", " << pixel[3] << '\n';
                return 16;
            }
        }
        glDisable (GL_BLEND);
        glBindFramebuffer (GL_FRAMEBUFFER, 0);
        glDeleteFramebuffers (1, &framebuffer);
        glDeleteTextures (1, &textura);
        glDeleteVertexArrays (1, &vao);
        glDeleteProgram (programa);
        std::cout << "Compositing: actual framebuffer RGB and alpha passed for two translucent layers.\n";
    }
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
    const auto compilar = [validarGPU] (const std::string& vertice, const std::string& fragmento) {
        auto fontes = GLSLContext::get ().toGlsl (vertice, fragmento);
        if (!validarGPU) return fontes;
        const GLuint programa = glCreateProgram ();
        for (const auto& etapa : { std::pair {GL_VERTEX_SHADER, &fontes.first}, std::pair {GL_FRAGMENT_SHADER, &fontes.second} }) {
            const GLuint shader = glCreateShader (etapa.first);
            const char* codigo = etapa.second->c_str ();
            glShaderSource (shader, 1, &codigo, nullptr);
            glCompileShader (shader);
            GLint sucesso;
            glGetShaderiv (shader, GL_COMPILE_STATUS, &sucesso);
            if (!sucesso) {
                char log[4096] {};
                glGetShaderInfoLog (shader, sizeof (log), nullptr, log);
                throw std::runtime_error (std::string ("OpenGL compilation: ") + log);
            }
            glAttachShader (programa, shader);
            glDeleteShader (shader);
        }
        glLinkProgram (programa);
        GLint sucesso;
        glGetProgramiv (programa, GL_LINK_STATUS, &sucesso);
        if (!sucesso) {
            char log[4096] {};
            glGetProgramInfoLog (programa, sizeof (log), nullptr, log);
            throw std::runtime_error (std::string ("OpenGL linking: ") + log);
        }
        glDeleteProgram (programa);
        return fontes;
    };
    const std::string cabecalho = "#version 330\n";
    const std::string vertice = cabecalho + "out vec2 v_TexCoord; void main() { v_TexCoord=vec2(0.5); gl_Position=vec4(0.0); }";
    const std::string fragmento = cabecalho + "#define varying in\nvarying vec2 v_TexCoord;\nout vec4 color;\n"
        "void main() { v_TexCoord.xy += vec2(0.1); color = vec4(v_TexCoord, 0.0, 1.0); }";
    const auto fontes = compilar (vertice, writableTexCoord (fragmento));
    if (fontes.first.empty () || fontes.second.empty ()) return 2;
    const std::string somenteLeitura = "varying vec2 v_TexCoord; void main() { float x = v_TexCoord.x; }";
    if (writableTexCoord (somenteLeitura) != somenteLeitura) return 3;
    std::cout << "Shader compatibility: writable input compiles; read-only input preserved.\n";
    const WallpaperEngine::Assets::AssetLocator localizador (nullptr);
    const WallpaperEngine::Data::Model::ComboMap combinacoes;
    const WallpaperEngine::Data::Model::ShaderConstantMap constantes;
    const WallpaperEngine::Data::Model::TextureMap texturas;
    Shader copia (localizador, "commands/copy", combinacoes, combinacoes, texturas, texturas, constantes);
    const auto shadersCopia = compilar (copia.vertex (), copia.fragment ());
    if (shadersCopia.first.empty () || shadersCopia.second.empty ()) return 4;
    std::cout << "Built-in copy command: vertex and fragment shaders compile.\n";
    const std::string verticeCondicional = cabecalho + "#define WIDE 0\n#if WIDE\nout vec4 v_TexCoord;\n"
        "#else\nout vec2 v_TexCoord;\n#endif\nvoid main(){v_TexCoord=vec2(0.5);gl_Position=vec4(0.0);}";
    const std::string fragmentoSimples = cabecalho + "in vec2 v_TexCoord; out vec4 color;"
        "void main(){color=vec4(v_TexCoord,0.0,1.0);}";
    const auto condicional = compilar (verticeCondicional, fragmentoSimples);
    if (condicional.first.empty () || condicional.second.empty ()) return 6;
    for (const auto& dimensoes : { std::pair {4, 2}, std::pair {2, 4}, std::pair {3, 2} }) {
        const auto v = cabecalho + "out vec" + std::to_string (dimensoes.first)
            + " uv; void main(){uv=vec" + std::to_string (dimensoes.first) + "(0.5);gl_Position=vec4(0.0);}";
        const auto f = cabecalho + "in vec" + std::to_string (dimensoes.second)
            + " uv; out vec4 color;void main(){color=vec4(uv.xy,0.0,1.0);}";
        const auto conversao = compilar (v, f);
        if (conversao.first.empty () || conversao.second.empty ()) return 7;
    }
    bool rejeitado = false;
    try { static_cast<void> (compilar (vertice, cabecalho + "void main(){INVALID SHADER;}")); }
    catch (const std::runtime_error& erro) {
        rejeitado = std::string (erro.what ()).find ("Fragment") != std::string::npos;
    }
    if (!rejeitado) return 5;
    std::cout << "Conditional interfaces, vector conversions and invalid shader diagnostics passed.\n";
    if (validarGPU) { std::cout << "OpenGL driver compilation/linking passed.\n"; glfwTerminate (); }
}
