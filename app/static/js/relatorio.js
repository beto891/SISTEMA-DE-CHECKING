document.addEventListener('DOMContentLoaded', function () {
    let tasks = [];

    // Busca os dados uma vez
    fetch('/tasks')
        .then(res => res.json())
        .then(data => {
            tasks = data;
            renderTable(tasks);
        });

    // Função para renderizar a tabela
    function renderTable(lista) {
    const termo = searchInput.value.toLowerCase();
    const tbody = document.querySelector('.table tbody');
    tbody.innerHTML = '';
    lista.forEach(task => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${task.id}</td>
            <td>${task.titulo || ''}</td>
            <td>${task.descricao || ''}</td>
            <td>${task.data_inicio || ''}</td>
            <td>${task.data_fim || ''}</td>
            <td>-</td>
        `;
        // Destaca em amarelo se o termo for encontrado na linha
        const texto = tr.textContent.toLowerCase();
        if (termo && texto.includes(termo)) {
            tr.style.backgroundColor = 'yellow';
        } else {
            tr.style.backgroundColor = '';
        }
        tbody.appendChild(tr);
    });
    document.getElementById('num-registros').textContent = lista.length;
}
    // Filtro por texto (barra de pesquisa)
    const searchInput = document.querySelector('input[placeholder="Procurar chamados..."]');
    searchInput.addEventListener('input', filtrar);

    // Filtro por status
    document.getElementById('status').addEventListener('change', filtrar);

    // Filtro por datas
    document.getElementById('data-inicio').addEventListener('change', filtrar);
    document.getElementById('data-fim').addEventListener('change', filtrar);

    function filtrar() {
        const termo = searchInput.value.toLowerCase();
        const status = document.getElementById('status').value;
        const dataInicio = document.getElementById('data-inicio').value;
        const dataFim = document.getElementById('data-fim').value;

        let filtrados = tasks.filter(task => {
            // Filtro texto
            let texto = `${task.id} ${task.titulo || ''} ${task.descricao || ''} ${task.data_inicio || ''} ${task.data_fim || ''}`.toLowerCase();
            let passaTexto = !termo || texto.includes(termo);
                

            // Filtro status
            let passaStatus = status === 'todos' ||
                (status === 'aberto' && (!task.data_fim || task.status === 'aberto')) ||
                (status === 'fechado' && (task.data_fim || task.status === 'fechado'));

            // Filtro data início
            let passaDataInicio = !dataInicio || (task.data_inicio && task.data_inicio >= dataInicio);

            // Filtro data fim
            let passaDataFim = !dataFim || (task.data_fim && task.data_fim <= dataFim);

            return passaTexto && passaStatus && passaDataInicio && passaDataFim;
        });

        renderTable(filtrados);
    }
});

document.querySelector('.exportar a').addEventListener('click', function(e) {
    e.preventDefault();

    // Seleciona as linhas visíveis da tabela
    const rows = Array.from(document.querySelectorAll('.table tbody tr'))
        .filter(row => row.style.display !== 'none');

    // Monta os dados para exportação
    const data = [
        ["ID", "Título", "Descrição", "Data de Criação", "Data de Conclusão", "Valor"]
    ];
    rows.forEach(row => {
        const cols = Array.from(row.querySelectorAll('td')).map(td => td.textContent);
        data.push(cols);
    });

    // Cria a planilha e exporta
    const ws = XLSX.utils.aoa_to_sheet(data);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Relatório");
    XLSX.writeFile(wb, "relatorio.xlsx");
});

