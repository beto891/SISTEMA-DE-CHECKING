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
    fetch('/api/campaign/mapa-dados')
        .then(response => {
            if (!response.ok) throw new Error('Erro ao buscar dados das campanhas.');
            return response.json();
        })
        .then(todasAsCampanhas => { // Renomeado para clareza
            if (!clusterGroup) return;
            
            // >>> FILTRO PRINCIPAL AQUI <<<
            // Cria uma nova lista contendo apenas as campanhas não concluídas.
            const campanhasAtivas = todasAsCampanhas.filter(campanha => !campanha.concluida);

            // Limpa as camadas antigas do mapa
            clusterGroup.clearLayers();
            for (const key in campaignMarkers) {
                delete campaignMarkers[key];
            }

            const agrupadas = {};
            // >>> USE A LISTA FILTRADA A PARTIR DE AGORA <<<
            campanhasAtivas.forEach(campanha => {
                const key = `${campanha.latitude},${campanha.longitude}`;
                if (!agrupadas[key]) {
                    agrupadas[key] = {
                        latitude: campanha.latitude,
                        longitude: campanha.longitude,
                        codigos: new Set(),
                        nomes: []
                    };
                }
                agrupadas[key].codigos.add(campanha.cod);
                const campanhaJaAdicionada = agrupadas[key].nomes.some(c => c.nome === campanha.nome);
                if (!campanhaJaAdicionada) {
                    agrupadas[key].nomes.push({
                        id: campanha.id,
                        nome: campanha.nome,
                        cod: campanha.cod
                    });
                }
            });

            // O resto da sua lógica para criar o HTML do popup e os marcadores
            // continua exatamente igual, pois já está dentro do .then()
            Object.values(agrupadas).forEach(item => {
                const linkStyle = "display: block; margin-bottom: 5px; word-wrap: break-word; white-space: normal;";
                const campanhasHtml = item.nomes.map(c =>
                    `<a href="#" class="btn-upload-campanha" data-campanha-cod="${c.cod}" data-campanha-nome="${c.nome}" style="${linkStyle}">${c.nome}</a>`
                ).join("");
                const espacosHtml = Array.from(item.codigos).join(', ') || 'N/A';
                const popupContent = `
                                    <div class="popup-grande" style="white-space: normal; word-wrap: break-word; font-size: 14px; line-height: 1.2;">
                                        <strong>Espaço:</strong> ${espacosHtml}<br>
                                        <strong style="margin-top: 10px; display: inline-block;">Campanhas:</strong><br>
                                        ${campanhasHtml}
                                    </div>
                                `; // Seu HTML do popup
                const popupOptions = { maxWidth: 500, minWidth: 280 };
                const marker = L.marker([item.latitude, item.longitude]).bindPopup(popupContent, popupOptions);

                item.nomes.forEach(c => {
                    if (c.id) campaignMarkers[c.id] = marker;
                });
                
                // ... (resto da sua lógica de adicionar layers) ...
                clusterGroup.addLayer(marker);
            });
            map.addLayer(clusterGroup);
        })
        .catch(error => console.error('Erro ao carregar campanhas:', error));
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
 * Normaliza uma string removendo acentos e convertendo para minúsculas.
 */
function normalizar(texto) {
    return texto.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
}

/**
 * Realiza a busca no mapa com base em um termo.
 */
function buscarNoMapa(termo) {
    const termoNormalizado = normalizar(termo);
    let encontrado = null;

    if (clusterGroup) {
        clusterGroup.eachLayer(layer => {
            const cod = normalizar(layer.options.espacoCod || '');
            const campanhas = (layer.options.campanhas || []).map(n => normalizar(n.nome));
            if (cod.includes(termoNormalizado) || campanhas.some(n => n.includes(termoNormalizado))) {
                encontrado = layer;
            }
        });
    }

    if (encontrado) {
        const latlng = encontrado.getLatLng();
        map.setView(latlng, 17);
        ajustarLayoutAposZoom();
        clusterGroup.zoomToShowLayer(encontrado, () => {
            encontrado.openPopup();
            ajustarLayoutAposZoom();
        });
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
            maxClusterRadius: 50,
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
        uploadBtn.addEventListener('click', function(event) {
            event.preventDefault();
            const fileInput = document.getElementById('imagemFile');
            if (fileInput.files.length === 0) {
                showBootstrapAlert('Por favor, selecione uma imagem para enviar.', 'warning');
                return;
            }

            const campanhaId = document.getElementById('campanhaIdInput').value;
            const campanhaNome = document.getElementById('campanhaNomeLabel').innerText.replace('Upload para a campanha: ', '');
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
                    const modal = bootstrap.Modal.getInstance(document.getElementById('uploadModal'));
                    if (modal) modal.hide();
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

    // --- Ouvinte de Evento para o Formulário de Importação de Planilha ---
$('#form-importar').off('submit').on('submit', function(event) {
    event.preventDefault();
    
    const form = this; // Guarda a referência do formulário
    const fileInput = form.querySelector('#arquivo');
    const alerta = document.getElementById('alerta-importacao');
    
    if (fileInput.files.length === 0) {
        alerta.innerHTML = `<div class="alert alert-danger" role="alert">Por favor, selecione uma planilha.</div>`;
        return;
    }
    
    // Opcional: Adicionar um estado de "carregando" no botão de importar
    const submitButton = $(this).find('button[type="submit"]');
    submitButton.prop('disabled', true).html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Importando...');

    const formData = new FormData(form);

    fetch('/api/importar-pontos', { 
        method: 'POST', 
        body: formData 
    })
    .then(response => {
        if (!response.ok) return response.json().then(err => { throw new Error(err.mensagem || 'Erro no servidor.') });
        return response.json();
    })
    .then(data => {
        const alertClass = data.success ? 'alert-success' : 'alert-danger';
        alerta.innerHTML = `<div class="alert ${alertClass}" role="alert">${data.mensagem}</div>`;
        
        if (data.success) {
            // ✅ 1. ATUALIZA O MAPA (já estava aqui)
            recarregarMapaComCampanhasAtivas(); // <<< CORRIGIDO

            // ✅ PONTO DE VERIFICAÇÃO:
            console.log("SUCESSO NA IMPORTAÇÃO. Tentando atualizar o mapa...");
            
            // ✅ 2. FECHA O MODAL APÓS UM ATRASO
            // Damos 2 segundos para o usuário ler a mensagem de sucesso.
            setTimeout(() => {
                 location.reload();
            }, 2000);
        }
    })
    .catch(error => {
        console.error('Erro na importação:', error);
        alerta.innerHTML = `<div class="alert alert-danger" role="alert">Erro: ${error.message}</div>`;

        setTimeout(() => {
                 location.reload();
            }, 2000);
    })
    .finally(() => {
        // ✅ 3. LIMPA O CAMPO DO ARQUIVO E RESTAURA O BOTÃO
        // Isso será executado sempre, com sucesso ou erro.
        form.reset(); // Limpa o input de arquivo e outros campos do formulário
        submitButton.prop('disabled', false).html('<i class="fas fa-upload mr-1"></i> Importar');
    });
});

    // --- Lógica para o Toast (se houver) ---
    // Usando jQuery se a página o tiver
    if (window.jQuery) {
        $('#toastImportar').toast('show');
    }
});