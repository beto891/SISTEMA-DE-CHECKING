// ✅ LÓGICA DE ALERTA COM EFEITO SONORO E TEMPO DE PERMANÊNCIA AJUSTADO
$(document).ready(function() {
const alertsContainer = $('#critical-alerts');
const hoje = new Date();
hoje.setHours(0, 0, 0, 0);
const delayMs = 500; // Atraso entre cada notificação

// Função para tocar o som de notificação
function tocarSomDeNotificacao() {
    const som = document.getElementById('notificationSound');
    if (som) {
        som.play().catch(e => console.log('Erro ao tocar o som:', e));
    }
}

const campanhasComAlerta = registros.filter(campanha => {
    if (campanha.percentual >= 100 || !campanha.data_criacao) return false;

    let dataCriacao = new Date(campanha.data_criacao);
    if (isNaN(dataCriacao.getTime())) {
        const parts = campanha.data_criacao.split(' ')[0].split('/');
        dataCriacao = new Date(`${parts[2]}-${parts[1]}-${parts[0]}`);
    }

    const diffDays = Math.floor((hoje - dataCriacao) / (1000 * 60 * 60 * 24));

    return diffDays > 5 || (diffDays >= 0 && diffDays <= 5);
});

if (campanhasComAlerta.length > 0) {
    alertsContainer.prepend(`<h6><i class="fas fa-exclamation-triangle"></i> Alertas de Campanhas (${campanhasComAlerta.length})</h6>`);
}

campanhasComAlerta.forEach((campanha, index) => {
    setTimeout(() => {
        let dataCriacao = new Date(campanha.data_criacao);
        if (isNaN(dataCriacao.getTime())) {
            const parts = campanha.data_criacao.split(' ')[0].split('/');
            dataCriacao = new Date(`${parts[2]}-${parts[1]}-${parts[0]}`);
        }

        const diffDays = Math.floor((hoje - dataCriacao) / (1000 * 60 * 60 * 24));
        let alertHtml = '';
        let diasTexto = diffDays === 0 ? `hoje` : (diffDays === 1 ? `há 1 dia` : `há ${diffDays} dias`);

        if (diffDays > 5) {
            alertHtml = `
                <div class="toast fade show" role="alert" aria-live="assertive" aria-atomic="true" data-autohide="true" data-delay="5000">
                    <div class="toast-header bg-danger text-white">
                    <strong class="mr-auto"><i class="fas fa-exclamation-circle mr-2"></i>Prazo Excedido</strong>
                    <button type="button" class="ml-2 mb-1 close" data-dismiss="toast" aria-label="Close">
                        <span aria-hidden="true">&times;</span>
                    </button>
                    </div>
                    <div class="toast-body">A campanha "<strong>${campanha.campanha}</strong>" foi criada ${diasTexto} e ainda não atingiu 100% da meta.</div>
                </div>`;
        } else if (diffDays >= 0 && diffDays <= 5) {
            alertHtml = `
                <div class="toast fade show" role="alert" aria-live="assertive" aria-atomic="true" data-autohide="true" data-delay="5000">
                    <div class="toast-header bg-warning text-dark">
                    <strong class="mr-auto"><i class="fas fa-clock mr-2"></i>Atenção ao Prazo</strong>
                    <button type="button" class="ml-2 mb-1 close" data-dismiss="toast" aria-label="Close">
                        <span aria-hidden="true">&times;</span>
                    </button>
                    </div>
                    <div class="toast-body">A campanha "<strong>${campanha.campanha}</strong>" foi criada ${diasTexto} e ainda não atingiu 100% da meta.</div>
                </div>`;
        }

        if (alertHtml) {
            const newToast = $(alertHtml).appendTo(alertsContainer);
            newToast.toast('show');
            tocarSomDeNotificacao(); // Chama a função para tocar o som
        }
    }, index * delayMs);
});
});