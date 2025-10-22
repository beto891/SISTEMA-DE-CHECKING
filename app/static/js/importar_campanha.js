// ✅ Importação AJAX com DOM pronto - VERSÃO CORRIGIDA PARA AJAX MAP UPDATE

document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("form-importar");
    if (!form) {
        console.warn("Formulário #form-importar não encontrado nesta página.");
        return; // Sai se o formulário não existir na página atual
    }

    const alerta = document.getElementById("alerta-importacao");
    const submitButton = $(form).find('button[type="submit"]'); // Usando jQuery pois já está na página

    form.addEventListener("submit", async function (event) {
        event.preventDefault(); // Impede o envio padrão e recarregamento da página

        const fileInput = form.querySelector('#arquivo');
        if (fileInput.files.length === 0) {
            alerta.innerHTML = `<div class="alert alert-danger alert-dismissible fade show" role="alert">
                Por favor, selecione uma planilha.
                <button type="button" class="close" data-dismiss="alert" aria-label="Fechar"><span aria-hidden="true">&times;</span></button>
            </div>`;
            return;
        }

        const formData = new FormData(this);

        // Mostra o estado de carregamento
        submitButton.prop('disabled', true).html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Importando...');
        alerta.innerHTML = ''; // Limpa alertas anteriores

        try {
            // Chama a API de importação correta
            const resposta = await fetch("/api/campaign/importar-campanhas", {
                method: "POST",
                body: formData
            });

            const resultado = await resposta.json();

            // Mostra a mensagem de resultado (sucesso ou erro)
            alerta.innerHTML = `
            <div class="alert ${resultado.success ? 'alert-success' : 'alert-danger'} alert-dismissible fade show" role="alert">
                ${resultado.mensagem}
                ${resultado.ignorados ? '<br><small>Linhas ignoradas: ' + resultado.ignorados + '</small>' : ''}
                <button type="button" class="close" data-dismiss="alert" aria-label="Fechar">
                <span aria-hidden="true">&times;</span>
                </button>
            </div>
            `;

            if (resultado.success) {
                console.log("Importação bem-sucedida. Tentando atualizar o mapa via AJAX...");

                // Tenta chamar a função para recarregar o mapa (definida em campanhas_map.js)
                if (typeof recarregarMapaComCampanhasAtivas === "function") {
                    recarregarMapaComCampanhasAtivas();
                    console.log("Mapa atualizado.");
                } else {
                    console.error("Função recarregarMapaComCampanhasAtivas não encontrada! O mapa não será atualizado dinamicamente.");
                    // Fallback: recarregar a página se a função não for encontrada
                    // setTimeout(() => { location.reload(); }, 2000); 
                }
                
                // Fecha o modal após 3 segundos para o usuário ler a mensagem
                setTimeout(() => {
                    const modalEl = document.getElementById('modalImportar');
                    if (modalEl) {
                         // Tenta obter instância existente ou cria uma nova
                         const modalInstance = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
                         modalInstance.hide();
                    }
                    // Remove o alerta após fechar o modal
                     const alertaElemento = alerta.querySelector(".alert");
                     if (alertaElemento) alertaElemento.remove();
                 }, 3000); 

            } else {
                 // Remove o alerta de erro após 5 segundos
                 setTimeout(() => {
                    const alertaElemento = alerta.querySelector(".alert");
                    if (alertaElemento) alertaElemento.remove();
                 }, 5000);
            }

        } catch (erro) {
            console.error('Erro na requisição de importação:', erro);
            alerta.innerHTML = `
            <div class="alert alert-danger alert-dismissible fade show" role="alert">
                ❌ Erro ao enviar a planilha: ${erro.message || 'Erro desconhecido.'}
                <button type="button" class="close" data-dismiss="alert" aria-label="Fechar">
                <span aria-hidden="true">&times;</span>
                </button>
            </div>
            `;
             // Remove o alerta de erro após 5 segundos
             setTimeout(() => {
                const alertaElemento = alerta.querySelector(".alert");
                if (alertaElemento) alertaElemento.remove();
             }, 5000);
        } finally {
             // Restaura o botão e limpa o formulário SEMPRE (sucesso ou erro)
             form.reset(); 
             submitButton.prop('disabled', false).html('<i class="fas fa-upload mr-1"></i> Importar');
        }
    });
});