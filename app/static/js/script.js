// Seleciona os elementos necessários
const addTaskButton = document.querySelectorAll('.add-task-button');
const formContainer = document.getElementById('form-container');
const closeButton = document.querySelector('.close-button');
const taskForm = document.getElementById('task-form');
const columns = document.querySelectorAll('.column');
const cardFormContainer = document.getElementById('card-form-container');
const cardFormCloseButton = document.querySelector('.close-card-form');
const cardForm = document.getElementById('card-form-agendado');
const cardformConcluido = document.getElementById('card-form-concluido');

let currentColumn = null;

// Fecha o formulário ao clicar no botão "X"
closeButton.addEventListener('click', function () {
    formContainer.style.display = 'none';
    taskForm.reset();
});

// Fecha o formulário adicional ao clicar no botão "X"
cardFormCloseButton.addEventListener('click', function () {
    cardFormContainer.style.display = 'none';
    cardForm.reset();
});

let formJustOpened = false;

window.addEventListener('mousedown', function (event) {
    if (
        formContainer.style.display === 'flex' &&
        !formContainer.contains(event.target) &&
        event.target !== formContainer
    ) {
        formContainer.style.display = 'none';
        taskForm.reset();
    }
    if (
        cardFormContainer.style.display === 'block' &&
        !cardFormContainer.querySelector('.card-form-content').contains(event.target)
    ) {
        cardFormContainer.style.display = 'none';
        cardForm.reset();
    }
    if (
        cardformConcluido.style.display === 'block' &&
        !cardformConcluido.querySelector('.card-form-content').contains(event.target)
    ) {
        cardformConcluido.style.display = 'none';
        if (typeof cardformConcluido.reset === 'function') {
            cardformConcluido.reset();
        }
        const form = cardformConcluido.querySelector('form');
        if (form) {
            form.reset();
        }
    }
});

window.addEventListener('keydown', function (event) {
    if (event.key === "Escape") {
        if (formContainer.style.display === 'flex') {
            formContainer.style.display = 'none';
            taskForm.reset();
        }
        if (cardFormContainer.style.display === 'block') {
            cardFormContainer.style.display = 'none';
            cardForm.reset();
        }
        if (cardformConcluido.style.display === 'block') {
            cardformConcluido.style.display = 'none';
            if (typeof cardformConcluido.reset === 'function'){
                cardformConcluido.reset();
            }
            const form = cardformConcluido.querySelector('form');
            if (form) {
                form.reset();
            }
        }
    }
});

addTaskButton.forEach(button => {
    button.addEventListener('click', function () {
        formContainer.style.display = 'flex';
        currentColumn = button.closest('.column');
        formJustOpened = true;
    });
});

// Carrega tarefas do back-end e adiciona ao Kanban ao iniciar
fetch('/tasks')
    .then(res => {
        if (res.status === 401) {
            window.location.href = '/login';
            return;
        }
        return res.json();
    })
    .then(tasks => {
        if (!tasks) return;
        tasks.forEach(task => {
            const novaTarefa = document.createElement('div');
            novaTarefa.classList.add('task');
            novaTarefa.setAttribute('draggable', 'true');
            novaTarefa.id = `task-${task.id}`;
            novaTarefa.innerHTML = `
                <strong>${task.titulo}</strong>
                <p><strong>Motivo:</strong> ${task.motivo || ''}</p>
                <p><strong>Tipo:</strong> ${task.estabelecimento || ''}</p>
                <p><strong>Localidade:</strong> ${task.localidade || ''}</p>
                <p>${task.descricao}</p>
            `;
            novaTarefa.addEventListener('click', function () {
                const agendadoColumn = document.getElementById('agendado'); 
                if (agendadoColumn.contains(novaTarefa)) {
                    openCardFormConcluido(novaTarefa);
                } else {
                    openCardForm(novaTarefa);
                }
            });
            novaTarefa.addEventListener('dragstart', dragStart);
            novaTarefa.addEventListener('dragend', dragEnd);

            const coluna = document.getElementById(task.status);
            if (coluna) {
                coluna.appendChild(novaTarefa);
            }
        });
        contadorTarefas();
    });

taskForm.addEventListener('submit', function (event) {
    event.preventDefault();

    const nEstabelecimento = document.querySelector('input[name="local"]:checked').value;
    const nMotivo = document.querySelector('input[name="tarefa"]:checked').value;
    const nId = document.getElementById('identificador').value; 
    const nDescricao = document.getElementById('task-details').value;
    const nCidade = document.getElementById('cidade').value;
    const nEstado = document.getElementById('inputState').value;

    const dados = {
        titulo: nId,
        motivo: nMotivo,
        estabelecimento: nEstabelecimento,
        localidade: `${nCidade}-${nEstado}`,
        descricao: nDescricao,
        status: "solicitacoes"
    };

    fetch('/tasks', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(dados)
    })
    .then(res => {
        if (res.status === 401) {
            window.location.href = '/login';
            return;
        }
        return res.json();
    })
    .then(task => {
        if (!task) return;
        const novaTarefa = document.createElement('div');
        novaTarefa.classList.add('task');
        novaTarefa.setAttribute('draggable', 'true');
        novaTarefa.id = `task-${task.id}`;
        novaTarefa.innerHTML = `
            <strong>${task.titulo}</strong>
            <p><strong>Motivo:</strong> ${task.motivo}</p>
            <p><strong>Tipo:</strong> ${task.estabelecimento}</p>
            <p><strong>Localidade:</strong> ${task.localidade}</p>
            <p>${task.descricao}</p>
        `;
        novaTarefa.addEventListener('click', function () {
            const agendadoColumn = document.getElementById('agendado'); 
            if (agendadoColumn.contains(novaTarefa)) {
                openCardFormConcluido(novaTarefa);
            } else {
                openCardForm(novaTarefa);
            }
        });
        novaTarefa.addEventListener('dragstart', dragStart);
        novaTarefa.addEventListener('dragend', dragEnd);

        document.getElementById('solicitacoes').appendChild(novaTarefa);
        contadorTarefas();
        formContainer.style.display = 'none';
        taskForm.reset();
    });
});

// Funções de arrastar e soltar
function dragStart(e) {
    e.dataTransfer.setData('text/plain', e.target.id);
    e.target.classList.add('dragging');
}

function dragEnd(e) {
    e.target.classList.remove('dragging');
}

columns.forEach(column => {
    column.addEventListener('dragover', dragOver);
    column.addEventListener('drop', drop);
});

function dragOver(e) {
    e.preventDefault();
}

function drop(e) {
    e.preventDefault();
    const taskElement = document.querySelector('.dragging');
    const newParent = e.target.closest('.space-y-5');

    if (newParent && taskElement) {
        newParent.appendChild(taskElement);
        taskElement.classList.remove('dragging');
        contadorTarefas();
    }
}

// Função para abrir o formulário adicional para fases das colunas
function openCardForm(taskElement) {
    cardFormContainer.style.display = 'block';

    cardForm.onsubmit = function (event) {
        event.preventDefault();

        const statusSelecionado = document.getElementById("status-agendado").value;
        const dataAgendada = document.getElementById("dataAgendamento").value;

        if (!dataAgendada || !statusSelecionado) {
            alert("Por favor, preencha todos os campos antes de salvar.");
            return;
        }

        let destino = null;
        let body = { status: statusSelecionado };

        if (statusSelecionado === "agendado") {
            destino = document.getElementById("agendado");
            body.data_inicio = dataAgendada;
        } else if (statusSelecionado === "concluido") {
            destino = document.getElementById("concluido");
            body.data_fim = new Date().toISOString().slice(0, 10);
        } else if (statusSelecionado === "cancelado") {
            destino = document.getElementById("cancelado");
            body.data_fim = new Date().toISOString().slice(0, 10);
        }

        if (destino) {
            destino.appendChild(taskElement);

            fetch(`/tasks/${taskElement.id.replace('task-', '')}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });

            taskElement.onclick = function(e) { e.stopPropagation(); };
            taskElement.style.cursor = "default";
            taskElement.removeAttribute('draggable');
        }

        contadorTarefas();
        cardFormContainer.style.display = 'none';
        cardForm.reset();
    };
}

function openCardFormConcluido(taskElement) {
    const agendadoColumn = document.getElementById('agendado');
    const concluidoColumn = document.getElementById('concluido');

    if (agendadoColumn && agendadoColumn.contains(taskElement)) {
        cardformConcluido.style.display = 'block';
        cardformConcluido.onsubmit = function (event){
            event.preventDefault();
            const statusSelecionado = document.getElementById("status-concluido").value;

            let destino = null;
            let body = { status: statusSelecionado };

            if (statusSelecionado === "concluido") {
                destino = concluidoColumn;
                body.data_fim = new Date().toISOString().slice(0, 10);
            } else if (statusSelecionado === "cancelado") {
                destino = document.getElementById("cancelado");
                body.data_fim = new Date().toISOString().slice(0, 10);
            }

            if (destino) {
                destino.appendChild(taskElement);

                fetch(`/tasks/${taskElement.id.replace('task-', '')}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body)
                });

                taskElement.onclick = null;
                taskElement.style.cursor = "default";
                taskElement.removeAttribute('draggable');
            }

            contadorTarefas();

            cardformConcluido.style.display = 'none';
            if (typeof cardformConcluido.reset === 'function') {
                cardformConcluido.reset();
            }
        };
    } else {
        console.log(`Tarefa ${taskElement.id} não está na coluna Agendado. Não é possível abrir o formulário.`);
    }
}   

function contadorTarefas() {
    document.getElementById("count-solicitacoes").textContent = document.querySelectorAll("#solicitacoes .task").length;
    document.getElementById("count-agendado").textContent = document.querySelectorAll("#agendado .task").length;
    document.getElementById("count-concluido").textContent = document.querySelectorAll("#concluido .task").length;
    document.getElementById("count-cancelado").textContent = document.querySelectorAll("#cancelado .task").length;
}

// Inicializa os contadores ao carregar a página
contadorTarefas();

// Supondo que seu input de pesquisa tem placeholder="Procurar cards..." e class="form-control me-2"
const searchInput = document.querySelector('input[placeholder="Procurar cards..."]');

searchInput.addEventListener('input', function () {
    const termo = this.value.toLowerCase();
    // Seleciona todos os cards
    document.querySelectorAll('.task').forEach(card => {
        // Pega o texto do card (pode customizar para buscar só em certos campos)
        const texto = card.textContent.toLowerCase();
        // Mostra ou esconde conforme o termo pesquisado
        if (texto.includes(termo)) {
            card.style.display = '';
        } else {
            card.style.display = 'none';
        }
    });
});

document.addEventListener('DOMContentLoaded', function () {
    const coluna = document.querySelector('#coluna-solicitacoes .scroll-area');
    const header = coluna.querySelector('.column-header1');

    coluna.addEventListener('scroll', function () {
        // Pega o primeiro card da coluna
        const firstCard = coluna.querySelector('.task');
        if (!firstCard) {
            header.classList.remove('blur');
            return;
        }
        // Pega a posição do card e do header
        const cardRect = firstCard.getBoundingClientRect();
        const headerRect = header.getBoundingClientRect();

        // Se o topo do card está atrás do header, aplica blur
        if (cardRect.top < headerRect.bottom) {
            header.classList.add('blur');
        } else {
            header.classList.remove('blur');
        }
    });
});