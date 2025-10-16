document.addEventListener('DOMContentLoaded', () => {
const campoBusca = document.getElementById('campoBuscaCampanha'); // insira esse input no template
const seletorStatus = document.getElementById('status');          // insira esse select no template
const tabela = document.getElementById('tabelaCampanhas');
const linhas = tabela.querySelectorAll('tbody > tr');

function normalizar(texto) {
return texto.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
}

function aplicarFiltros() {
const termo = normalizar(campoBusca.value);
const statusFiltro = seletorStatus.value;

linhas.forEach(linha => {
    const celulas = linha.querySelectorAll('td');
    const campanha = normalizar(celulas[0]?.textContent || '');
    const statusTexto = celulas[3]?.textContent.toLowerCase() || '';

    const status = statusTexto.includes('atingida') ? 'aberto' :
                    statusTexto.includes('abaixo')   ? 'fechado' : '';

    const correspondeNome = campanha.includes(termo);
    const correspondeStatus = statusFiltro === 'todos' || statusFiltro === status;

    linha.style.display = (correspondeNome && correspondeStatus) ? '' : 'none';
    linha.classList.toggle('tr-destaque', campanha === termo && correspondeStatus);
});
}

campoBusca.addEventListener('input', aplicarFiltros);
seletorStatus.addEventListener('change', aplicarFiltros);
});