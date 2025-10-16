document.addEventListener('DOMContentLoaded', () => {
const campoBusca = document.getElementById('campoBuscaUsuario');
const tabela = document.querySelector('table.table-bordered');
const linhas = tabela.querySelectorAll('tbody > tr');

function normalizar(texto) {
return texto.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
}

campoBusca.addEventListener('input', () => {
const termo = normalizar(campoBusca.value);

linhas.forEach(linha => {
    const nomeUsuario = normalizar(linha.cells[1]?.textContent || '');

    const visivel = nomeUsuario.includes(termo);
    linha.style.display = visivel ? '' : 'none';
    linha.classList.toggle('tr-destaque', nomeUsuario === termo);
});
});
});