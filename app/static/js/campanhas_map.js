/**
 * =================================================================
 * SCRIPT CONSOLIDADO PARA O MAPA E DASHBOARD
 * @version 7.0 (Estrutura Corrigida e Completa)
 * @description Define todas as funções e depois anexa os eventos
 * para garantir o escopo correto e a funcionalidade.
 * =================================================================
 */

// --------------------------------------------------
// 1. VARIÁVEIS GLOBAIS
// --------------------------------------------------
let map;
let highlightedMarkers = []; // Guarda os marcadores atualmente destacados
let clusterGroup;
const campaignMarkers = {};

// --------------------------------------------------
// 2. DEFINIÇÃO DE TODAS AS FUNÇÕES
// --------------------------------------------------

/**
 * Exibe uma notificação de Bootstrap que desaparece sozinha.
 * @param {string} message - A mensagem a ser exibida.
 * @param {string} type - O tipo de alerta ('success', 'danger', 'warning', 'info').
 * @param {number} duration - Duração em milissegundos para o alerta ficar visível.
 */
function showBootstrapAlert(message, type = 'success', duration = 4000) {
    const container = document.getElementById('notification-container');
    if (!container) {
        console.error('Container de notificação #notification-container não encontrado.');
        alert(message);
        return;
    }
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.role = 'alert';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    container.appendChild(alertDiv);
    const bsAlert = new bootstrap.Alert(alertDiv);
    setTimeout(() => {
        bsAlert.close();
    }, duration);
}

// // Ícone Padrão (Círculo Azul)
// const defaultIcon = L.divIcon({
//     className: 'leaflet-div-icon-individual', 
//     iconSize: [12, 12] // Tamanho padrão (pequeno)
// });

// // Ícone Destacado (Círculo Vermelho Pulsante)
// const highlightedIcon = L.divIcon({
//     className: 'leaflet-div-icon-individual marker-highlighted-icon', // Adiciona a classe da animação
//     iconSize: [16, 16] // Tamanho base UM POUCO MAIOR que o padrão
// });

/**
 * Busca e exibe as localizações dos usuários no mapa.
 */
function fetchAndDisplayUserLocations() {
    fetch('/api/user-locations')
        .then(response => {
            if (!response.ok) throw new Error('Erro ao buscar localizações de usuários.');
            return response.json();
        })
        .then(locations => {
            locations.forEach(location => {
                const marker = L.marker([location.latitude, location.longitude])
                    .bindPopup(`
                        <div class="popup-location">
                            <strong>Usuário ID:</strong> ${location.user_id}<br>
                            <strong>Latitude:</strong> ${location.latitude}<br>
                            <strong>Longitude:</strong> ${location.longitude}<br>
                            <strong>Última atualização:</strong> ${new Date(location.timestamp).toLocaleString()}
                        </div>
                    `);
                if (clusterGroup) {
                    clusterGroup.addLayer(marker);
                }
            });
        })
        .catch(error => console.error('Erro ao carregar localizações de usuários:', error));
}

// Em campanhas_map.js

/**
 * ✅ FUNÇÃO RENOMEADA E MODIFICADA
 * Busca os dados de TODAS as campanhas, filtra as ativas e exibe no mapa.
 */
function recarregarMapaComCampanhasAtivas() {
    console.log("[Mapa] Iniciando recarregamento..."); 
    fetch('/api/campaign/mapa-dados')
        .then(response => {
            if (!response.ok) throw new Error(`Erro ${response.status} ao buscar dados das campanhas.`);
            return response.json();
        })
        .then(todasAsCampanhas => {
            console.log("[Mapa] Dados recebidos da API:", todasAsCampanhas); 

            if (!clusterGroup) {
                console.error("[Mapa] Erro: clusterGroup não inicializado!");
                return;
            }
            
            const campanhasAtivas = todasAsCampanhas.filter(campanha => !campanha.concluida);
            console.log(`[Mapa] Campanhas ativas (após filtro !concluida): ${campanhasAtivas.length}`, campanhasAtivas); 

            clusterGroup.clearLayers();
            for (const key in campaignMarkers) { delete campaignMarkers[key]; }

            const agrupadas = {};
            // Loop de Agrupamento
            campanhasAtivas.forEach((campanha) => { // Removido 'idx' pois não era usado corretamente
                if (campanha.latitude == null || campanha.longitude == null) {
                    // ✅ CORREÇÃO APLICADA AQUI
                    console.warn(`[Mapa] Campanha ID ${campanha.id} (${campanha.nome}) sem coordenadas válidas:`, campanha); 
                    return; // Pula esta campanha
                }
                const key = `${campanha.latitude},${campanha.longitude}`;
                if (!agrupadas[key]) {
                    agrupadas[key] = {
                        latitude: campanha.latitude, longitude: campanha.longitude,
                        codigos: new Set(), nomes: []
                    };
                }
                agrupadas[key].codigos.add(campanha.cod);
                if (!agrupadas[key].nomes.some(c => c.nome === campanha.nome)) {
                     agrupadas[key].nomes.push({ id: campanha.id, nome: campanha.nome, cod: campanha.cod });
                }
            });
            console.log("[Mapa] Objeto 'agrupadas' criado:", agrupadas); 

            const gruposParaRenderizar = Object.values(agrupadas);
            console.log(`[Mapa] Número de grupos para renderizar: ${gruposParaRenderizar.length}`); 

            // Loop de Renderização
            gruposParaRenderizar.forEach((item, index) => { 
                console.log(`[Mapa] Renderizando grupo ${index}:`, item); 
                try { 
                    const campanhasHtml = item.nomes.map(c =>
                        `<a href="#" class="btn-upload-campanha" data-campanha-cod="${c.cod}" data-campanha-nome="${c.nome}">${c.nome}</a>`
                    ).join('<br>');
                    const espacosHtml = Array.from(item.codigos).join(', ') || 'N/A';
                    const popupContent = `
                        <div class="popup-grande" style="white-space: normal; word-wrap: break-word; font-size: 14px; line-height: 1.2;">
                            <strong>Espaços:</strong> ${espacosHtml}<br>
                            <strong style="margin-top: 10px; display: inline-block;">Campanhas:</strong><br>
                            ${campanhasHtml}
                        </div>
                    `; 
                    const popupOptions = { maxWidth: 500, minWidth: 280 };

                    if (item.latitude == null || item.longitude == null) {
                         console.error("[Mapa] ERRO GRAVE: Item agrupado sem coordenadas válidas:", item);
                         return; 
                    }

                    const marker = L.marker([item.latitude, item.longitude]).bindPopup(popupContent, popupOptions);

                    const codigosString = Array.from(item.codigos).join(', ');
                    marker.options.espacoCod = codigosString; 
                    marker.options.campanhas = item.nomes; 
                    marker.options.campanhasCount = item.nomes.length;

                    console.log(`[Mapa] Marcador ${index} Dados Armazenados:`, { cod: marker.options.espacoCod, nomes: marker.options.campanhas.map(c=>c.nome) }); 

                    item.nomes.forEach(c => { if (c.id) campaignMarkers[c.id] = marker; });
                    clusterGroup.addLayer(marker);

                } catch (renderError) {
                     console.error(`[Mapa] Erro ao renderizar grupo ${index}:`, item, renderError);
                }
            });
            
            if (gruposParaRenderizar.length > 0) {
                 map.addLayer(clusterGroup);
                 console.log("[Mapa] Mapa e clusters atualizados com sucesso."); 
            } else {
                 console.warn("[Mapa] Nenhum grupo para renderizar no mapa."); 
            }
        })
        .catch(error => {
            console.error('[Mapa] Erro CRÍTICO no fetch ou processamento:', error);
             showBootstrapAlert(`Erro ao carregar os dados do mapa: ${error.message}`, 'danger');
        });
}

/**
 * Abre o modal de upload para uma campanha específica.
 */
function abrirFormularioUpload(campanhaCod, campanhaNome) {
    const uploadModalEl = document.getElementById('uploadModal');
    if (uploadModalEl) {
        const uploadModal = new bootstrap.Modal(uploadModalEl);
        uploadModal.show();
        document.getElementById('campanhaIdInput').value = campanhaCod;
        document.getElementById('campanhaNomeLabel').innerText = `Upload para a campanha: ${campanhaNome}`;
    }
}

/**
 * ✅ VERSÃO CORRIGIDA
 * Normaliza uma string removendo acentos e convertendo para minúsculas.
 */
function normalizar(texto) {
    // Garante que o texto é uma string antes de tentar normalizar
    if (typeof texto !== 'string') {
        return '';
    }
    // O método normalize("NFD") separa os caracteres dos seus acentos,
    // e a expressão regular /[\u0300-\u036f]/g remove esses acentos.
    return texto.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
}

/**
 * ✅ FUNÇÃO AJUSTADA PARA ABRIR POPUPS MÚLTIPLOS
 * Realiza a busca no mapa. Se encontrar 1 resultado, foca e abre o popup.
 * Se encontrar múltiplos, ajusta o mapa e ABRE O POPUP de todos os encontrados.
 */
function buscarNoMapa(termo) {
    const termoNormalizado = normalizar(termo);
    console.log(`[Busca] Iniciando busca por termo normalizado: "${termoNormalizado}"`); 
    const encontrados = []; 

    // --- 1. Limpa o destaque anterior (se você voltar a usar destaque depois) ---
    // (A lógica de limpar destaque com setIcon/highlightedMarkers permaneceria aqui)
    // if (highlightedMarkers.length > 0) { ... highlightedMarkers = []; }

    if (!clusterGroup) {
         console.error("[Busca] Erro: clusterGroup não está definido.");
         return; 
    }

    try {
        // --- 2. Percorre os marcadores e busca correspondências ---
        clusterGroup.eachLayer(layer => {
            const rawEspacoCod = layer.options?.espacoCod; 
            const rawCampanhasArray = layer.options?.campanhas; 
            const codNormalizado = normalizar(rawEspacoCod || ''); 
            const nomesCampanhasNormalizados = (Array.isArray(rawCampanhasArray) ? rawCampanhasArray : [])
                .map(campanhaObj => normalizar(campanhaObj?.nome || ''))
                .filter(nome => nome); 

            const achouNoCod = codNormalizado.includes(termoNormalizado);
            const achouNoNome = nomesCampanhasNormalizados.some(n => n.includes(termoNormalizado));

            if (achouNoCod || achouNoNome) {
                encontrados.push(layer); 
            }
        });
    } catch (error) { 
        console.error("[Busca] Erro durante a varredura dos marcadores:", error);
        showBootstrapAlert("Ocorreu um erro durante a busca.", 'danger');
        return; 
    }

    // --- 3. AÇÃO COM BASE NO NÚMERO DE RESULTADOS ---
    if (encontrados.length === 0) {
        // Nenhum resultado
        console.log("[Busca] Nenhum ponto encontrado para: " + termo); 
        showBootstrapAlert(`Nenhum ponto encontrado para "${termo}"`, 'info', 3000); 

    } else if (encontrados.length === 1) {
        // Exatamente UM resultado (Foco e abre popup)
        const unicoEncontrado = encontrados[0];
        const latlng = unicoEncontrado.getLatLng();
        console.log("[Busca] 1 Marcador encontrado. Focando..."); 
        map.setView(latlng, 17); // Zoom próximo
        ajustarLayoutAposZoom();
        
        setTimeout(() => { 
            try {
                if (clusterGroup.hasLayer(unicoEncontrado)) {
                     clusterGroup.zoomToShowLayer(unicoEncontrado, () => {
                        unicoEncontrado.openPopup();
                        ajustarLayoutAposZoom();
                        console.log("[Busca] Popup único aberto via zoomToShowLayer."); 
                    });
                } else {
                     unicoEncontrado.openPopup(); 
                }
            } catch (zoomError) {
                 console.error("[Busca] Erro ao tentar dar zoom/abrir popup único:", zoomError);
                 try { unicoEncontrado.openPopup(); } catch (popupError) { console.error("Erro ao abrir popup único diretamente:", popupError); }
            }
        }, 300); 

    } else {
        // MÚLTIPLOS resultados (Ajusta zoom e ABRE TODOS os popups)
        console.log(`[Busca] ${encontrados.length} marcadores encontrados. Ajustando visão e abrindo popups.`); 
        showBootstrapAlert(`Exibindo ${encontrados.length} locais encontrados para "${termo}"`, 'success', 4000);

        // Cria um grupo temporário apenas com os marcadores encontrados
        const grupoResultados = L.featureGroup(encontrados); 
        const bounds = grupoResultados.getBounds(); 

        // Ajusta o mapa para mostrar todos os marcadores
        if (bounds.isValid()) { 
            map.fitBounds(bounds.pad(0.1)); 
        } else {
            console.warn("[Busca] Limites inválidos para múltiplos resultados.");
        }
        ajustarLayoutAposZoom(); 

        // --- ✅ NOVA PARTE: Abrir popups múltiplos ---
        // Adiciona um pequeno atraso para garantir que o 'fitBounds' termine
        setTimeout(() => {
            console.log("[Busca] Tentando abrir popups múltiplos...");
            encontrados.forEach((marker, index) => {
                try {
                    marker.openPopup(); // Tenta abrir o popup de cada marcador encontrado
                    console.log(`[Busca] Popup ${index + 1}/${encontrados.length} aberto.`);
                } catch (popupError) {
                    console.error(`[Busca] Erro ao abrir popup múltiplo ${index}:`, popupError);
                }
            });
        }, 500); // Atraso de 500ms (meio segundo) - ajuste se necessário
    }
}

/**
 * Ajusta o layout do mapa e elementos sobrepostos após o zoom.
 */
function ajustarLayoutAposZoom() {
    setTimeout(() => {
        if (map) map.invalidateSize();
        const card = document.querySelector('.card');
        if (card) {
            card.style.top = '80px';
            card.style.right = '20px';
        }
    }, 400);
}


// --------------------------------------------------
// 3. ANEXAR OS OUVINTES DE EVENTOS (GATILHOS)
// --------------------------------------------------
document.addEventListener('DOMContentLoaded', function() {
    console.log("DOM totalmente carregado. Anexando todos os ouvintes de evento...");

    // --- Inicialização do Mapa Leaflet ---
    if (document.getElementById('map')) {
        map = L.map('map', { center: [-23.5505, -46.6333], zoom: 5, minZoom: 3 });
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        }).addTo(map);

        clusterGroup = L.markerClusterGroup({
            maxClusterRadius: 80,
            iconCreateFunction: function(cluster) {
                let totalCampanhas = 0;
                cluster.getAllChildMarkers().forEach(marker => {
                    totalCampanhas += marker.options.campanhasCount || 1;
                });
                let color = totalCampanhas > 10 ? 'rgb(255, 0, 0)' : totalCampanhas > 5 ? 'rgb(255, 140, 0)' : 'rgb(255, 255, 0)';
                return L.divIcon({
                    html: `<div style="background-color:${color}" class="marker-cluster-small">${totalCampanhas}</div>`,
                    className: '',
                    iconSize: [50, 50]
                });
            }
        });

        map.on('popupopen', function(e) {
            const popup = e.popup.getElement();
            const uploadLinks = popup.querySelectorAll('.btn-upload-campanha');
            uploadLinks.forEach(link => {
                link.addEventListener('click', function(event) {
                    event.preventDefault();
                    abrirFormularioUpload(event.currentTarget.dataset.campanhaCod, event.currentTarget.dataset.campanhaNome);
                });
            });
        });

        map.on('zoomend', ajustarLayoutAposZoom);

        recarregarMapaComCampanhasAtivas(); // Carrega as campanhas ativas inicialmente
        fetchAndDisplayUserLocations();
    }

    // --- Ouvinte de Evento para o Campo de Busca do Mapa ---
    const campoBusca = document.getElementById('campoBuscaMapa');
    if (campoBusca) {
        campoBusca.addEventListener('input', () => {
            const valor = campoBusca.value.trim();
            if (valor.length >= 2) {
                buscarNoMapa(valor);
            } else {
                if (map) {
                    map.setView([-23.5505, -46.6333], 5);
                    map.closePopup();
                }
                ajustarLayoutAposZoom();
            }
        });
    }

    // --- Ouvinte de Evento para o Botão de Upload de Foto ---
    const uploadBtn = document.getElementById('uploadBtn');
    if (uploadBtn) {

        // ✅ LOG 1: Antes de anexar o evento (pode remover se não precisar mais)
        console.log('Tentando anexar evento ao uploadBtn...'); 

        uploadBtn.addEventListener('click', function(event) {

            // ✅ LOG 2: Evento de clique acionado (pode remover se não precisar mais)
            console.log('Evento de clique no uploadBtn acionado.'); 

            event.preventDefault();
            const fileInput = document.getElementById('imagemFile');
            if (fileInput.files.length === 0) {
                showBootstrapAlert('Por favor, selecione uma imagem para enviar.', 'warning');
                return;
            }

            const campanhaId = document.getElementById('campanhaIdInput').value;
            // Corrigido para pegar o 'cod' em vez do 'id' se necessário, ajuste conforme o seu HTML
            // const campanhaCod = document.getElementById('campanhaIdInput').value; 
            const campanhaNome = document.getElementById('campanhaNomeLabel').innerText.replace('Upload para a campanha: ', '');
            
            // Ajuste aqui se campanhaId for na verdade o 'cod'
            if (!campanhaId || !campanhaNome) { 
                showBootstrapAlert('Erro: O código ou nome da campanha não foi encontrado.', 'danger');
                return;
            }

            const uploadBtnText = document.getElementById('uploadBtnText');
            const uploadSpinner = document.getElementById('uploadSpinner');
            uploadBtnText.textContent = 'Enviando...';
            uploadSpinner.classList.remove('d-none');
            uploadBtn.disabled = true;

            const formData = new FormData();
            // Garanta que está enviando 'cod' como esperado pela API /api/upload/foto
            formData.append('cod', campanhaId); 
            formData.append('nome', campanhaNome);

            for (const file of fileInput.files) {
                formData.append('imagem', file);
            }

            fetch('/api/upload/foto', {
                method: 'POST',
                body: formData
            })
            .then(response => {
                if (!response.ok) throw new Error(`Erro HTTP: ${response.status}`);
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    showBootstrapAlert('Upload realizado com sucesso!');
                    // ✅ CORREÇÃO AQUI: Usa jQuery para fechar o modal Bootstrap 4
                    $('#uploadModal').modal('hide'); 
                } else {
                    showBootstrapAlert(`Erro no upload: ${data.mensagem}`, 'danger');
                }
            })
            .catch(error => {
                console.error('Erro de rede:', error);
                showBootstrapAlert('Erro de rede ao tentar fazer o upload.', 'danger');
            })
            .finally(() => {
                uploadBtnText.innerHTML = '<i class="bi bi-cloud-upload-fill me-1"></i> Enviar';
                uploadSpinner.classList.add('d-none');
                uploadBtn.disabled = false;
                // Limpa o valor do input de arquivo, fazendo-o voltar ao estado inicial.
                $('#imagemFile').val(null); 
            });
        });
    }


    // --- Lógica para o Toast (se houver) ---
    // Usando jQuery se a página o tiver
    if (window.jQuery) {
        $('#toastImportar').toast('show');
    }
});