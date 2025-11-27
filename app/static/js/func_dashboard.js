/**
 * =================================================================
 * SCRIPT CONSOLIDADO PARA DASHBOARD E MAPA
 * @version 10.2 (Ajustado para Responsividade Desktop/Mobile)
 * @description Define todas as funções e anexa todos os eventos de forma segura
 * usando um único bloco $(document).ready().
 * =================================================================
 */

// --------------------------------------------------
// 1. VARIÁVEIS GLOBAIS
// --------------------------------------------------
let map;
let clusterGroup;
const campaignMarkers = {};

// --------------------------------------------------
// 2. DEFINIÇÃO DE TODAS AS FUNÇÕES
// --------------------------------------------------

// --- FUNÇÕES DE NOTIFICAÇÃO E UI ---

/**
 * Exibe uma notificação de Bootstrap (compatível com Bootstrap 4 e jQuery).
 */
function showBootstrapAlert(message, type = 'success', duration = 5000) {
    const container = $('#notification-container');
    if (container.length === 0) {
        console.error('Container de notificação #notification-container não encontrado no HTML.');
        alert(message);
        return;
    }
    const alertDiv = $(`<div class="alert alert-${type} alert-dismissible fade show" role="alert">${message}</div>`);
    const closeButton = $('<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button>');
    alertDiv.append(closeButton);
    container.append(alertDiv);
    if (duration > 0) {
        setTimeout(() => {
            alertDiv.fadeTo(500, 0).slideUp(500, function() { $(this).remove(); });
        }, duration);
    }
}

function renderizarSpinner(container, mensagem) {
    if (container) container.innerHTML = `<div class="text-center p-5"><div class="spinner-border text-primary" role="status"></div><p class="mt-2">${mensagem}</p></div>`;
}

function renderizarMensagem(container, mensagem, tipo = 'danger') {
    if (container) container.innerHTML = `<div class="alert alert-${tipo} text-center">${mensagem}</div>`;
}

function normalizarUrlDropbox(url) {
    if (!url || typeof url !== 'string' || !url.includes('dropbox.com')) {
        return url;
    }
    try {
        const urlObj = new URL(url);
        urlObj.hostname = 'dl.dropboxusercontent.com';
        urlObj.searchParams.set('dl', '1');
        return urlObj.toString();
    } catch (e) {
        console.error("Erro ao normalizar URL do Dropbox:", e, url);
        return url;
    }
}

// --- FUNÇÃO DE GERAÇÃO DE PDF ---
async function gerarRelatorioPDF() {
    const form = document.getElementById('formPdfGeracao');
    const btn = document.getElementById('btnGerarPdf'); 

    // 1. Validação
    if (!form.checkValidity()) {
        alert('⚠️ Preencha todos os campos obrigatórios.');
        form.reportValidity();
        return;
    }

    // 2. Feedback Visual
    const conteudoOriginal = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processando...';

    try {
        $('#modalPdfInfo').modal('hide');
        showBootstrapAlert('Iniciando geração do PDF...', 'info');

        const formData = new FormData(form);

        // 4. Envio
        const response = await fetch('/gerar-pdf', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const erro = await response.json(); 
            throw new Error(erro.mensagem || 'Erro desconhecido no servidor.');
        }

        // 5. Download (Sucesso)
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        
        const nomeArquivo = formData.get('nome') || 'Campanha'; 
        a.download = `Relatorio_${nomeArquivo}.pdf`;
        
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);

        showBootstrapAlert('✅ PDF gerado com sucesso!', 'success');

    } catch (error) {
        console.error(error);
        showBootstrapAlert(`Erro: ${error.message}`, 'danger');
        $('#modalPdfInfo').modal('show');
    } finally {
        btn.disabled = false;
        btn.innerHTML = conteudoOriginal;
    }
}

// --- FUNÇÕES DE AÇÃO DE MODAIS (PDF, GALERIA, EDIÇÃO, EXCLUSÃO) ---

function abrirModalPdf(campanhaNome) {
    $('#inputCampanha').val(campanhaNome);
    $('#modalPdfInfo').modal('show');
}


function abrirGaleria(campanhaId, nomeCampanha) {
    if (!nomeCampanha) {
        console.error("Nome da campanha inválido ao abrir galeria.");
        return;
    }
    const galeriaModal = $('#modalGaleria');
    galeriaModal.data('campanha-nome', nomeCampanha);
    //galeriaModal.find('#modalGaleriaLabel').text(`Campanha: ${nomeCampanha}`);
    $('#galeriaTabs .nav-link').removeClass('active');
    $('#tabAtivas').addClass('active');
    galeriaModal.modal('show');
    carregarImagens(false);
}

function editarCampanha(campanhaId) {
    if (!campanhaId) return;
    fetch(`/api/campaign/${campanhaId}`)
        .then(response => {
            if (!response.ok) throw new Error('Campanha não encontrada.');
            return response.json();
        })
        .then(campanha => {
            $('#editCampanhaId').val(campanha.id);
            $('#editCampanhaNome').val(campanha.nome);
            $('#modalEdicaoCampanha').modal('show');
        })
        .catch(error => {
            console.error('Erro ao buscar dados da campanha:', error);
            showBootstrapAlert('Não foi possível carregar os dados para edição.', 'danger');
        });
}

async function salvarEdicaoCampanha() {
    const campanhaId = $('#editCampanhaId').val();
    const novoNome = $('#editCampanhaNome').val();
    if (!campanhaId || !novoNome) {
        showBootstrapAlert('Dados inválidos para salvar.', 'warning');
        return;
    }
    try {
        const response = await fetch(`/api/campaign/${campanhaId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ novo_nome: novoNome })
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.mensagem || 'Erro ao salvar.');
        
        showBootstrapAlert(data.mensagem, 'success');
        $('#modalEdicaoCampanha').modal('hide');

        // Atualiza a tabela desktop
        const linhaDaTabela = $(`.content-desktop .btn-galeria[data-id="${campanhaId}"]`).closest('tr');
        if (linhaDaTabela.length) {
            linhaDaTabela.find('td:first').text(novoNome);
            linhaDaTabela.find('[data-nome]').attr('data-nome', novoNome);
        }
        // Nota: A atualização dos cards mobile precisa ser feita via recarregamento ou re-renderização do Jinja
        // Se você usar filtro/pesquisa em JS, precisará atualizar a lista de registros.

    } catch (error) {
        console.error('Erro ao salvar edição:', error);
        showBootstrapAlert(`Falha ao salvar: ${error.message}`, 'danger');
    }
}

/**
 * Prepara e abre o modal de exclusão de campanha.
 */
function abrirModalExclusaoCampanha(campanhaId, campanhaNome) {
    const modal = $('#confirmacaoExclusaoModal');
    
    modal.find('#nomeCampanhaParaExcluir').text(campanhaNome);
    
    modal.find('#btnConfirmarExclusaoCampanha').data('campanha-id', campanhaId);

    modal.modal('show');
}

/**
 * Executa a exclusão de campanha via API.
 */
async function confirmarExclusaoCampanha() {
    const campanhaId = $('#btnConfirmarExclusaoCampanha').data('campanha-id');
    
    $('#confirmacaoExclusaoModal').modal('hide');

    if (!campanhaId) {
        showBootstrapAlert('Erro: ID da campanha não encontrado.', 'danger');
        return;
    }
    try {
        const response = await fetch(`/api/campaign/${campanhaId}`, { method: 'DELETE' });
        const data = await response.json();
        if (!response.ok) throw new Error(data.mensagem || 'Erro ao excluir.');
        
        showBootstrapAlert(data.mensagem, 'success');
        
        // Remove a linha da tabela desktop e o card mobile
        $(`[data-id="${campanhaId}"]`).closest('tr, .campaign-card').remove(); 

    } catch (error) {
        console.error('Erro ao excluir campanha:', error);
        showBootstrapAlert(`Erro: ${error.message}`, 'danger');
    }
}

// --- FUNÇÕES DA GALERIA ---
async function carregarImagens(mostrarLixeira) {
    const container = document.getElementById('galeriaContainer');
    const nomeCampanha = $('#modalGaleria').data('campanha-nome');
    if (!nomeCampanha) return;

    renderizarSpinner(container, 'Carregando imagens...');
    try {
        const endpoint = mostrarLixeira ? 'imagens_lixeira' : 'imagens';
        const response = await fetch(`/api/upload/${endpoint}?campanha_nome=${encodeURIComponent(nomeCampanha)}`);
        if (!response.ok) throw new Error(`Erro de rede (${response.status})`);
        const data = await response.json();
        if (data.success) {
            await renderizarGaleria(data.imagens, mostrarLixeira);
        } else {
            throw new Error(data.mensagem || 'Falha ao buscar imagens.');
        }
    } catch (error) {
        console.error('[carregarImagens] Erro:', error);
        renderizarMensagem(container, `<strong>Erro ao carregar galeria.</strong><br>${error.message}`);
    }
}

async function renderizarGaleria(imagens, isLixeira) {
    const container = document.getElementById('galeriaContainer');
    
    // 1. MODIFICAÇÃO NO INÍCIO: Capturar o modal e o nome da campanha.
    const galeriaModal = $('#modalGaleria');
    const nomeCampanha = galeriaModal.data('campanha-nome');

    if (!imagens || imagens.length === 0) {
        renderizarMensagem(container, 'Nenhuma imagem encontrada.', 'info');
        // Atualiza o título para 0 fotos, caso não haja imagens
        galeriaModal.find('#modalGaleriaLabel').text(`Galeria - ${nomeCampanha} (0 Fotos)`);
        return;
    }
    
    // O restante do código de processamento de cards...
    const promessasDosCards = imagens.map(img => new Promise(resolve => {
        if (!img || !img.url || !img.path || !img.id) {
            console.warn('Objeto de imagem inválido ou sem ID, descartando:', img);
            resolve(null);
            return;
        }
        const urlFinal = normalizarUrlDropbox(img.url);
        const nomeArquivo = img.path.split('/').pop();
        const imageLoader = new Image();
        imageLoader.onload = () => {
            const botoesHtml = isLixeira
                ? `<button class="btn btn-sm btn-success mx-1" data-acao="restaurar" data-id="${img.id}" title="Restaurar"><i class="fas fa-undo"></i></button>
                   <button class="btn btn-sm btn-danger mx-1" data-acao="excluir_definitivo" data-id="${img.id}" data-nome="${nomeArquivo}" title="Excluir"><i class="fas fa-trash-alt"></i></button>`
                : `<a href="${urlFinal}" target="_blank" rel="noopener noreferrer" class="btn btn-sm btn-primary mx-1" title="Visualizar"><i class="fas fa-eye"></i></a>
                   <button class="btn btn-sm btn-outline-danger mx-1" data-acao="deletar" data-id="${img.id}" data-nome="${nomeArquivo}" title="Lixeira"><i class="fas fa-trash"></i></button>`;
            const cardHtml = `
                <div class="col-xl-3 col-lg-4 col-md-6 mb-4" id="imagem-card-${img.id}">
                    <div class="card h-100 shadow-sm gallery-card">
                        <div class="gallery-img-container"><img src="${urlFinal}" class="card-img-top" alt="${nomeArquivo}" loading="lazy"></div>
                        <div class="card-body text-center d-flex flex-column">
                            <h6 class="card-title" title="${nomeArquivo}">${nomeArquivo}</h6>
                            <div class="mt-auto">${botoesHtml}</div>
                        </div>
                    </div>
                </div>`;
            resolve(cardHtml);
        };
        imageLoader.onerror = () => {
            console.warn('Imagem quebrada não será exibida:', urlFinal);
            resolve(null);
        };
        imageLoader.src = urlFinal;
    }));
    
    const cardsRenderizaveis = (await Promise.all(promessasDosCards)).filter(card => card);

    if (cardsRenderizaveis.length > 0) {
        container.innerHTML = `<div class="row">${cardsRenderizaveis.join('')}</div>`;
        
        // 2. MODIFICAÇÃO APÓS RENDERIZAÇÃO: Atualizar o contador final
        const contagemFinal = cardsRenderizaveis.length;
        galeriaModal.find('#modalGaleriaLabel').text(`Galeria - ${nomeCampanha} (${contagemFinal} Fotos)`);
        
    } else {
        renderizarMensagem(container, 'Nenhuma imagem válida pôde ser carregada.', 'warning');
        
        // 2. MODIFICAÇÃO APÓS RENDERIZAÇÃO: Atualizar para 0 fotos se a filtragem falhar
        galeriaModal.find('#modalGaleriaLabel').text(`Galeria - ${nomeCampanha} (0 Fotos)`);
    }
}


function confirmarAcaoImagem(acao, id, nome) {
    const modal = $('#modalConfirmacao');
    const corpoModal = modal.find('.modal-body');
    const botaoConfirmar = modal.find('#btnConfirmarExclusaoImagem');
    const mensagem = acao === 'deletar' ? `Tem certeza que deseja mover a imagem "${nome}" para a lixeira?` : `<strong>Atenção!</strong><br>Tem certeza que deseja excluir permanentemente a imagem "${nome}"?`;
    corpoModal.html(mensagem);
    botaoConfirmar.off('click').on('click', () => {
        executarAcaoImagem(acao, id);
        modal.modal('hide');
    });
    modal.modal('show');
}

async function executarAcaoImagem(acao, id) {
    if (!id || id === 'undefined') {
        showBootstrapAlert("Erro: ID da imagem inválido.", 'danger');
        return;
    }
    const endpoints = { 'deletar': '/api/image/delete-to-trash', 'restaurar': '/api/image/restore', 'excluir_definitivo': '/api/image/delete-permanent' };
    const endpoint = endpoints[acao];
    if (!endpoint) return;
    try {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image_id: id }) 
        });
        const data = await response.json();
        if (!response.ok || !data.success) throw new Error(data.mensagem || 'Ocorreu um erro no servidor.');
        showBootstrapAlert(data.mensagem, 'success');
        const isLixeiraAtiva = $('#tabLixeira').hasClass('active');
        carregarImagens(isLixeiraAtiva);
    } catch (error) {
        console.error(`[executarAcaoImagem] Erro:`, error);
        showBootstrapAlert(`Falha na operação: ${error.message}`, 'danger');
    }
}


// --------------------------------------------------
// 3. INICIALIZAÇÃO E ANEXAÇÃO DE EVENTOS
// --------------------------------------------------
$(document).ready(function() {
    console.log("DOM carregado. Anexando todos os ouvintes de evento...");

    // --- CARREGAMENTO INICIAL DO DASHBOARD ---
    if (typeof recarregarMapaComCampanhasAtivas === 'function') {
        recarregarMapaComCampanhasAtivas();
    } else {
        console.error("A função 'recarregarMapaComCampanhasAtivas' não foi encontrada. Verifique a ordem de importação dos seus scripts.");
    }

    // =======================================================
    // ✅ AJUSTE PRINCIPAL 1: Unificação do Gerenciador de Cliques 
    // Anexa os cliques em ambos os contêineres: Tabela (#tabelaCampanhas) e Cartões (#mobileCampanhasContainer)
    // =======================================================
    $('#tabelaCampanhas, #mobileCampanhasContainer').on('click', function(event) {
        const target = event.target;
        
        const pdfButton = target.closest('.btn-pdf');
        if (pdfButton) {
            // dataset funciona em botões de ambos os layouts
            abrirModalPdf(pdfButton.dataset.nome);
            return;
        }
        const galleryButton = target.closest('.btn-galeria');
        if (galleryButton) {
            abrirGaleria(galleryButton.dataset.id, galleryButton.dataset.nome);
            return;
        }
        
        // Estes botões estão primariamente (ou exclusivamente) no desktop (dropdown),
        // mas são delegados pelo clique no container de desktop.
        const editButton = target.closest('.btn-editar-campanha');
        if (editButton) {
            editarCampanha(editButton.dataset.id);
            return;
        }
        const deleteButton = target.closest('.btn-excluir-campanha');
        if (deleteButton) {
            abrirModalExclusaoCampanha(deleteButton.dataset.id, deleteButton.dataset.nome);
            return;
        }
    });

    // =======================================================
    // ✅ AJUSTE PRINCIPAL 2: Unificação do Gerenciador de Status (Checkbox/Switch)
    // Anexa a mudança de status em ambos os contêineres.
    // =======================================================
    $('#tabelaCampanhas, #mobileCampanhasContainer').on('change', '.campaign-status-checkbox', async function() {
        // O restante da lógica permanece igual, pois ele lê o 'data-nome' do checkbox, 
        // que é o mesmo em ambos os layouts (desktop e mobile-status-{{ r.id }})
        
        // 1. Pega o NOME da campanha, e não mais o ID
        const checkbox = $(this);
        const campanhaNome = checkbox.data('nome');
        const isConcluida = checkbox.is(':checked');

        // Validação
        if (!campanhaNome) {
            showBootstrapAlert('Erro: Não foi possível identificar a campanha.', 'danger');
            return;
        }

        try {
            // 2. Chama a rota da API
            const response = await fetch(`/api/campaign/status-by-name`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                // 3. Envia o NOME da campanha junto com o status
                body: JSON.stringify({ nome: campanhaNome, concluida: isConcluida })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.mensagem || 'Erro ao atualizar status.');
            }

            showBootstrapAlert(data.mensagem, 'success');

            // Atualiza o mapa para refletir a mudança
            if (typeof recarregarMapaComCampanhasAtivas === 'function') {
                recarregarMapaComCampanhasAtivas();
            }
            
            // ✅ ATUALIZA O GRÁFICO
            if (typeof recarregarGraficoDoDashboard === 'function') {
                recarregarGraficoDoDashboard();
            }

        } catch (error) {
            console.error('Erro ao atualizar status da campanha:', error);
            showBootstrapAlert(error.message, 'danger');
            
            // Desfaz a ação do usuário no checkbox se a API falhar
            checkbox.prop('checked', !isConcluida);
        }
    });

    // --- GERENCIADORES DE CLIQUES PARA MODAIS E GALERIA (Inalterados, pois já usavam seletores mais genéricos) ---

    $('#galeriaTabs').on('click', '.nav-link', function(e) {
        e.preventDefault();
        const isLixeira = $(this).attr('id') === 'tabLixeira';
        $('#galeriaTabs .nav-link').removeClass('active');
        $(this).addClass('active');
        carregarImagens(isLixeira);
    });

    $('#galeriaContainer').on('click', 'button[data-acao]', function() {
        const { acao, id, nome } = this.dataset;
        if (acao === 'deletar' || acao === 'excluir_definitivo') {
            confirmarAcaoImagem(acao, id, nome);
        } else if (acao === 'restaurar') {
            executarAcaoImagem(acao, id);
        }
    });
    
    $('#btnSalvarEdicao').on('click', salvarEdicaoCampanha);
    $('#btnConfirmarExclusaoCampanha').on('click', confirmarExclusaoCampanha);
    $('#btnGerarPdf').on('click', function(e) {
        e.preventDefault(); // Impede o submit padrão do formulário
        gerarRelatorioPDF();
    });
    $('#inputImagem').on('change', function() {
        $('#nomeArquivo').val(this.files.length > 0 ? this.files[0].name : 'Nenhum arquivo selecionado');
    });

    $('#modalEdicaoCampanha').on('hidden.bs.modal', function () {
        $(this).find('#editCampanhaId').val('');
        $(this).find('#editCampanhaNome').val('');
    });
});