document.addEventListener('DOMContentLoaded', () => {
const campoBusca = document.getElementById('campoBuscaCampanha');
const seletorStatus = document.getElementById('status');
const tabela = document.getElementById('tabelaCampanhas');
const linhas = tabela.querySelectorAll('tbody > tr'); // só as linhas de dados

function normalizar(texto) {
return texto.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
}

function aplicarFiltros() {
const termo = normalizar(campoBusca.value);
const statusFiltro = seletorStatus.value;

linhas.forEach(linha => {
    const celulaCampanha = linha.querySelector('td:nth-child(1)');
    const celulaStatus = linha.querySelector('td:nth-child(5)');

    const nome = normalizar(celulaCampanha?.textContent || '');
    const statusTexto = celulaStatus?.textContent || '';

    const status = normalizar(statusTexto).includes('atingida') ? 'aberto' :
            normalizar(statusTexto).includes('abaixo')   ? 'fechado' : '';

    const correspondeNome = nome.includes(termo);
    const correspondeStatus = statusFiltro === 'todos' || statusFiltro === status;

    linha.style.display = (correspondeNome && correspondeStatus) ? '' : 'none';
    linha.classList.toggle('tr-destaque', nome === termo && correspondeStatus);
});
}

campoBusca.addEventListener('input', aplicarFiltros);
seletorStatus.addEventListener('change', aplicarFiltros);
});