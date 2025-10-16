// Verifica se o elemento do mapa existe antes de inicializar o Leaflet
if (document.getElementById('map')) {
    const map = L.map('map', {
        center: [-23.5505, -46.6333],
        zoom: 5,
        minZoom: 3
    });

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);

    const clusterGroup = L.markerClusterGroup({
        maxClusterRadius: 50,
        iconCreateFunction: function (cluster) {
            let totalCampanhas = 0;
            cluster.getAllChildMarkers().forEach(marker => {
                totalCampanhas += marker.options.campanhasCount || 1;
            });
            
            let color = 'rgb(255, 255, 0)'; // Amarelo
            if (totalCampanhas > 10) {
                color = 'rgb(255, 0, 0)'; // Vermelho
            } else if (totalCampanhas > 5) {
                color = 'rgb(255, 140, 0)'; // Laranja
            }
            return L.divIcon({
                html: `<div style="background-color:${color}" class="marker-cluster-small">${totalCampanhas}</div>`,
                className: '',
                iconSize: [50, 50]
            });
        }
    });

    // Função para buscar e exibir as localizações dos usuários
    function fetchAndDisplayUserLocations() {
        fetch('/api/user-locations')
            .then(response => {
                if (!response.ok) {
                    throw new Error('Erro ao buscar localizações de usuários.');
                }
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
                    clusterGroup.addLayer(marker);
                });
                map.addLayer(clusterGroup);
            })
            .catch(error => {
                console.error('Erro ao carregar localizações de usuários:', error);
            });
    }

    // Função para buscar e exibir os pontos das campanhas com links
    function fetchAndDisplayCampaigns() {
        fetch('/api/campaign/mapa-dados')
            .then(response => {
                if (!response.ok) {
                    throw new Error('Erro ao buscar dados das campanhas.');
                }
                return response.json();
            })
            .then(campanhas => {
                const agrupadas = {};
                campanhas.forEach(campanha => {
                    const key = `${campanha.latitude},${campanha.longitude}`;
                    if (!agrupadas[key]) {
                        agrupadas[key] = {
                            latitude: campanha.latitude,
                            longitude: campanha.longitude,
                            codigos: new Set(),
                            nomes: [],
                            nomeEspaco: campanha.nome
                        };
                    }
                    agrupadas[key].codigos.add(campanha.cod);
                    const campanhaJaAdicionada = agrupadas[key].nomes.some(c => c.nome === campanha.nome);
                    if (!campanhaJaAdicionada) {
                         agrupadas[key].nomes.push({
                            id: campanha.id,
                            nome: campanha.nome
                        });
                    }
                });

                Object.values(agrupadas).forEach(item => {
                    const campanhasHtml = item.nomes.map(c => 
                        `<a href="#" onclick="abrirFormularioUpload('${c.id}', '${c.nome}')">${c.nome}</a>`
                    ).join("<br>");

                    const marker = L.marker([item.latitude, item.longitude])
                        .bindPopup(
                            `<div class="popup-grande">
                                <strong>Espaços:</strong> ${item.nomeEspaco}<br> 
                                <strong>Campanhas:</strong><br>${campanhasHtml}
                            </div>`
                        );
                    marker.options.espacoCod = Array.from(item.codigos).join(', ');
                    marker.options.campanhas = item.nomes;
                    marker.options.campanhasCount = item.nomes.length;
                    clusterGroup.addLayer(marker);
                });
                map.addLayer(clusterGroup);
            })
            .catch(error => {
                console.error('Erro ao carregar campanhas:', error);
            });
    }

    // Função para lidar com o clique no link de upload
    function abrirFormularioUpload(campanhaId, campanhaNome) {
        const modal = new bootstrap.Modal(document.getElementById('uploadModal'));
        document.getElementById('campanhaIdInput').value = campanhaId;
        document.getElementById('campanhaNomeLabel').innerText = `Upload para a campanha: ${campanhaNome}`;
        modal.show();
    }
    
    window.abrirFormularioUpload = abrirFormularioUpload;

    // Funções de busca
    // 🔧 Função para normalizar texto (remove acentos e espaço extra)
    function normalizar(texto) {
        return texto.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
    }

    // 🎯 Função principal para buscar no mapa
    function buscarNoMapa(termo) {
        const termoNormalizado = normalizar(termo);
        let encontrado = null;

        clusterGroup.eachLayer(layer => {
            const cod = normalizar(layer.options.espacoCod || '');
            const campanhas = (layer.options.campanhas || []).map(n => normalizar(n.nome));
            const porCod = cod.includes(termoNormalizado);
            const porCampanha = campanhas.some(n => n.includes(termoNormalizado));

            if (porCod || porCampanha) {
                encontrado = layer;
            }
        });

        if (encontrado) {
            const latlng = encontrado.getLatLng();
            map.setView(latlng, 11);
            ajustarLayoutAposZoom();

            clusterGroup.zoomToShowLayer(encontrado, () => {
                encontrado.openPopup();
                ajustarLayoutAposZoom();
            });
        } else {
            alert("Nenhum ponto encontrado para: " + termo);
        }
    }

    // ✅ CORREÇÃO AQUI: o ID correto da barra de pesquisa é `campoBuscaCampanha`
    const campoBusca = document.getElementById('campoBuscaCampanha');
    if (campoBusca) {
        campoBusca.addEventListener('input', () => {
            const valor = campoBusca.value.trim();
            if (valor.length >= 2) {
                buscarNoMapa(valor);
            } else {
                map.setView([-23.5505, -46.6333], 5);
                map.closePopup();
                ajustarLayoutAposZoom();
            }
        });
    }

    // Outras funções (mantidas)
    function ajustarLayoutAposZoom() {
        setTimeout(() => {
            map.invalidateSize();
            const card = document.querySelector('.card');
            if (card) {
                card.style.top = '80px';
                card.style.right = '20px';
            }
        }, 400);
    }
    
    map.on('zoomend', ajustarLayoutAposZoom);

    fetchAndDisplayCampaigns();
    fetchAndDisplayUserLocations();

}

$(document).ready(function () {
    setTimeout(function () {
        $('#toastImportar').toast('show');
    }, 2000); // ⏱️ 2 segundos de atraso
});
