/**
 * =================================================================
 * SCRIPT CONSOLIDADO PARA DASHBOARD E MAPA
 * @version 10.1 (Final, Completo e Corrigido)
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

// --- FUNÇÕES DE AÇÃO DE MODAIS (PDF, GALERIA, EDIÇÃO, EXCLUSÃO) ---

function abrirModalPdf(campanhaNome) {
    $('#inputCampanha').val(campanhaNome);
    $('#modalPdfInfo').modal('show');
}

function confirmarGeracao() {
    const form = document.getElementById('formPdfGeracao');
    if (!form.checkValidity()) {
        alert('⚠️ Preencha todos os campos obrigatórios.');
        form.reportValidity();
        return;
    }
    form.submit();
    $('#modalPdfInfo').modal('hide');
}

function abrirGaleria(campanhaId, nomeCampanha) {
    if (!nomeCampanha) {
        console.error("Nome da campanha inválido ao abrir galeria.");
        return;
    }
    const galeriaModal = $('#modalGaleria');
    galeriaModal.data('campanha-nome', nomeCampanha);
    galeriaModal.find('#modalGaleriaLabel').text(`Campanha: ${nomeCampanha}`);
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

        const linhaDaTabela = $(`.btn-galeria[data-id="${campanhaId}"]`).closest('tr');
        if (linhaDaTabela.length) {
            linhaDaTabela.find('td:first').text(novoNome);
            linhaDaTabela.find('[data-nome]').attr('data-nome', novoNome);
        }
    } catch (error) {
        console.error('Erro ao salvar edição:', error);
        showBootstrapAlert(`Falha ao salvar: ${error.message}`, 'danger');
    }
}

/**
 * ✅ FUNÇÃO AJUSTADA: Agora ela SÓ prepara e abre o modal de exclusão.
 */
function abrirModalExclusaoCampanha(campanhaId, campanhaNome) {
    const modal = $('#confirmacaoExclusaoModal');
    
    // Preenche o modal com os dados da campanha
    modal.find('#nomeCampanhaParaExcluir').text(campanhaNome);
    
    // Armazena o ID no próprio botão de confirmação para ser lido depois pelo ouvinte de evento
    modal.find('#btnConfirmarExclusaoCampanha').data('campanha-id', campanhaId);

    modal.modal('show');
}

/**
 * ✅ FUNÇÃO AJUSTADA: Chamada pelo ouvinte de evento fixo.
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
        $(`.btn-galeria[data-id="${campanhaId}"]`).closest('tr').remove();
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
    if (!imagens || imagens.length === 0) {
        renderizarMensagem(container, 'Nenhuma imagem encontrada.', 'info');
        return;
    }
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
    } else {
        renderizarMensagem(container, 'Nenhuma imagem válida pôde ser carregada.', 'warning');
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

    // --- Gerenciador de cliques para a TABELA PRINCIPAL ---
    $('#tabelaCampanhas').on('click', function(event) {
        const target = event.target;
        const pdfButton = target.closest('.btn-pdf');
        if (pdfButton) {
            abrirModalPdf(pdfButton.dataset.nome);
            return;
        }
        const galleryButton = target.closest('.btn-galeria');
        if (galleryButton) {
            abrirGaleria(galleryButton.dataset.id, galleryButton.dataset.nome);
            return;
        }
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

    // --- Gerenciador de cliques para as ABAS DA GALERIA ---
    $('#galeriaTabs').on('click', '.nav-link', function(e) {
        e.preventDefault();
        const isLixeira = $(this).attr('id') === 'tabLixeira';
        $('#galeriaTabs .nav-link').removeClass('active');
        $(this).addClass('active');
        carregarImagens(isLixeira);
    });

    // --- Gerenciador de cliques para os botões de AÇÃO DA GALERIA ---
    $('#galeriaContainer').on('click', 'button[data-acao]', function() {
        const botao = this;
        const { acao, id, nome } = botao.dataset;
        if (acao === 'deletar' || acao === 'excluir_definitivo') {
            confirmarAcaoImagem(acao, id, nome);
        } else if (acao === 'restaurar') {
            executarAcaoImagem(acao, id);
        }
    });
    
    // --- Outros Listeners para botões de confirmação em modais ---
    $('#btnSalvarEdicao').on('click', salvarEdicaoCampanha);
    $('#btnConfirmarExclusaoCampanha').on('click', confirmarExclusaoCampanha);
    $('#btnGerarPdf').on('click', confirmarGeracao);
    $('#inputImagem').on('change', function() { // Para o modal de PDF
        $('#nomeArquivo').val(this.files.length > 0 ? this.files[0].name : 'Nenhum arquivo selecionado');
    });

    // Limpa o formulário de edição quando o modal é fechado
    $('#modalEdicaoCampanha').on('hidden.bs.modal', function () {
        $(this).find('#editCampanhaId').val('');
        $(this).find('#editCampanhaNome').val('');
    });
});