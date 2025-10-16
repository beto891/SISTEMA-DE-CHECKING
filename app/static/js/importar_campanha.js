//✅ Importação AJAX com DOM pronto

document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("form-importar");
    if (!form) return;

    form.addEventListener("submit", async function (event) {
    event.preventDefault();
    const formData = new FormData(this);

    try {
        const resposta = await fetch("/api/campaign/importar-campanhas", {
        method: "POST",
        body: formData
        });

        const resultado = await resposta.json();

        const alerta = document.getElementById("alerta-importacao");
        alerta.innerHTML = `
        <div class="alert ${resultado.success ? 'alert-success' : 'alert-danger'} alert-dismissible fade show" role="alert">
            ${resultado.mensagem}
            ${resultado.ignorados ? '<br><small>Linhas ignoradas: ' + resultado.ignorados + '</small>' : ''}
            <button type="button" class="close" data-dismiss="alert" aria-label="Fechar">
            <span aria-hidden="true">&times;</span>
            </button>
        </div>
        `;

        function atualizarMapa() {
        fetch("/api/campaign/mapa-dados")
            .then(res => res.json())
            .then(pontos => {
            // Aqui você remove os marcadores antigos e adiciona os novos
            pontos.forEach(p => {
                L.marker([p.latitude, p.longitude])
                .addTo(map)
                .bindPopup(p.nome);
            });
            });
        }

        if (resultado.success && typeof atualizarMapa === "function") {
        atualizarMapa();
        }

        setTimeout(() => {
        const alertaElemento = document.querySelector(".alert");
        if (alertaElemento) alertaElemento.remove();
        }, 5000);

    } catch (erro) {
        document.getElementById("alerta-importacao").innerHTML = `
        <div class="alert alert-danger alert-dismissible fade show" role="alert">
            ❌ Erro ao enviar a planilha.
            <button type="button" class="close" data-dismiss="alert" aria-label="Fechar">
            <span aria-hidden="true">&times;</span>
            </button>
        </div>
        `;
        setTimeout(() => {
        const alertaElemento = document.querySelector(".alert");
        if (alertaElemento) alertaElemento.remove();
        }, 5000);
    }
    });
});