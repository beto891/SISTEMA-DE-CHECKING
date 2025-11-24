// Variáveis globais para controlar o marcador do usuário
let userMarker = null;
let userCircle = null;
let watchId = null; // Para poder parar o rastreamento se necessário

function iniciarRastreamentoUsuario() {
    if (!navigator.geolocation) {
        console.log("Geolocalização não é suportada pelo seu navegador.");
        return;
    }

    // Opções para alta precisão (GPS)
    const options = {
        enableHighAccuracy: true, 
        timeout: 10000,
        maximumAge: 0
    };

    // Inicia o monitoramento (watchPosition atualiza sempre que mudar)
    watchId = navigator.geolocation.watchPosition(success, error, options);
}

function success(pos) {
    const lat = pos.coords.latitude;
    const lng = pos.coords.longitude;
    const accuracy = pos.coords.accuracy; // Precisão em metros

    // 1. Se o marcador ainda não existe, cria ele
    if (!userMarker) {
        // Cria o ícone personalizado via CSS
        const userIcon = L.divIcon({
            className: 'user-location-marker',
            iconSize: [16, 16],
            iconAnchor: [8, 8] // Centraliza o ponto
        });

        userMarker = L.marker([lat, lng], {icon: userIcon}).addTo(map);
        userMarker.bindPopup("<b>Você está aqui</b>").openPopup();

        // Círculo azul claro indicando a área de precisão
        userCircle = L.circle([lat, lng], {
            radius: accuracy,
            color: '#4285F4',
            fillColor: '#4285F4',
            fillOpacity: 0.15,
            weight: 1
        }).addTo(map);

        // Centraliza o mapa no usuário na primeira vez
        map.setView([lat, lng], 15);
    } else {
        // 2. Se já existe, apenas atualiza a posição (animação suave)
        userMarker.setLatLng([lat, lng]);
        userCircle.setLatLng([lat, lng]);
        userCircle.setRadius(accuracy);
    }

    // (Opcional) Enviar localização para o backend se você tiver aquela rota configurada
    // enviarLocalizacaoParaBackend(lat, lng);
}

function error(err) {
    console.warn(`ERRO GPS (${err.code}): ${err.message}`);
    if (err.code === 1) {
        alert("Por favor, permita o acesso à localização para ver sua posição no mapa.");
    }
}

// --- INTEGRAÇÃO: Chame essa função na inicialização do seu mapa ---
// Procure onde você tem algo como $(document).ready ou initMap e adicione:
// iniciarRastreamentoUsuario();