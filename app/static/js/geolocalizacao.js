// Variáveis globais para controle
let userMarker = null;
let userCircle = null;
let watchId = null;

// 1. Função Principal (A Receita)
function iniciarRastreamentoUsuario() {
    // Verifica se o mapa existe (foi criado pelo outro script)
    if (typeof map === 'undefined' || map === null) {
        console.warn("Mapa ainda não carregado. Tentando novamente em 1s...");
        setTimeout(iniciarRastreamentoUsuario, 1000);
        return;
    }

    if (!navigator.geolocation) {
        console.log("Navegador não suporta geolocalização.");
        return;
    }

    console.log("📍 Iniciando rastreamento GPS...");
    
    const options = {
        enableHighAccuracy: true, 
        timeout: 10000,
        maximumAge: 0
    };

    // Começa a vigiar a posição
    watchId = navigator.geolocation.watchPosition(successLocation, errorLocation, options);
}

// 2. Sucesso: Desenha/Atualiza o ícone
function successLocation(pos) {
    const lat = pos.coords.latitude;
    const lng = pos.coords.longitude;
    const accuracy = pos.coords.accuracy;

    // Define o ícone (precisa do CSS que te passei antes)
    const userIcon = L.divIcon({
        className: 'user-location-marker',
        iconSize: [50, 50],
        iconAnchor: [50, 50]
    });

    // Se o marcador não existe, cria
    if (!userMarker) {
        userMarker = L.marker([lat, lng], {icon: userIcon}).addTo(map);
        userMarker.bindPopup("<b>Você está aqui</b>");
        
        userCircle = L.circle([lat, lng], {
            radius: accuracy,
            color: '#4285F4',
            fillColor: '#4285F4',
            fillOpacity: 0.15,
            weight: 1
        }).addTo(map);

        // Opcional: Centraliza a câmera no usuário na primeira vez que acha
         map.setView([lat, lng], 16); 
    } else {
        // Se já existe, só move (para não ficar piscando)
        userMarker.setLatLng([lat, lng]);
        userCircle.setLatLng([lat, lng]);
        userCircle.setRadius(accuracy);
    }
}

// 3. Erro
function errorLocation(err) {
    console.warn(`ERRO GPS (${err.code}): ${err.message}`);
}

// --- O GATILHO AUTOMÁTICO (O que faltava) ---
$(document).ready(function() {
    // Chama a função assim que a página estiver pronta
    iniciarRastreamentoUsuario();
});