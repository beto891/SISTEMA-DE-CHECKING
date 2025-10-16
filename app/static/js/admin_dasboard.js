const BASE = '/api/upload';

$(document).ready(() => {
  console.log('[admin_dashboard] script carregado');

  // Quando o usuário seleciona uma campanha
  $('#seletorCampanha').on('change', function () {
    const nomeCampanha = $(this).val();
    if (!nomeCampanha) return;
    carregarEspacosComImagens(nomeCampanha);
  });

  // Botão "Ver Imagens"
  $(document).on('click', '.btn-ver-imagens', function () {
    const cod = this.getAttribute('data-cod');
    const nome = this.getAttribute('data-nome');
    console.log('[admin_dashboard] Ver Imagens clicado ➞', { cod, nome });
    abrirGaleria(cod, nome);
  });

  // Limpar galeria ao fechar modal
  $('#modalGaleria').on('hidden.bs.modal', () => {
    console.log('[admin_dashboard] modalGaleria fechado');
    $('#galeriaContainer').empty();
  });
});

function carregarEspacosComImagens(nomeCampanha) {
  console.log('[carregarEspacosComImagens] iniciando com ➞', nomeCampanha);
  const url = `${BASE}/campanha-com-imagens/${encodeURIComponent(nomeCampanha)}`;

  fetch(url)
    .then(res => {
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res.json();
    })
    .then(data => {
      if (!Array.isArray(data) || !data.length) {
        $('#tabelaCampanhas').html('<tr><td colspan="5">Nenhum espaço com imagens.</td></tr>');
        return;
      }

      let html = '';
      data.forEach(e => {
        html += `
          <tr>
            <td>${e.nome}</td>
            <td>—</td>
            <td>—</td>
            <td>—</td>
            <td>
              <button class="btn btn-sm btn-primary btn-ver-imagens"
                      data-cod="${e.cod}"
                      data-nome="${e.nome}">
                Ver Imagens
              </button>
            </td>
          </tr>
        `;
      });

      $('#tabelaCampanhas').html(html);
    })
    .catch(err => {
      console.error('[carregarEspacosComImagens] erro no fetch ➞', err);
      $('#tabelaCampanhas').html(`
        <tr>
          <td colspan="5" class="text-danger">Erro ao carregar os espaços. Tente novamente.</td>
        </tr>
      `);
    });
}

function abrirGaleria(cod, nomeCampanha) {
  if (!cod || !nomeCampanha) {
    return $('#galeriaContainer')
      .html('<p class="text-danger">Dados da campanha inválidos.</p>');
  }

  $('#galeriaContainer').html(`
    <div class="text-center text-muted">
      <div class="spinner-border" role="status"></div>
      <p class="mt-2">Carregando imagens…</p>
    </div>
  `);
  $('#modalGaleria').modal('show');

  const url = `${BASE}/listar/${encodeURIComponent(cod)}/${encodeURIComponent(nomeCampanha)}`;

  fetch(url)
    .then(res => {
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res.json();
    })
    .then(data => {
      if (!data.success || !Array.isArray(data.imagens) || !data.imagens.length) {
        return $('#galeriaContainer')
          .html('<p class="text-warning">Nenhuma imagem encontrada.</p>');
      }

      const grupos = data.imagens.reduce((acc, img) => {
        const esp = img.espaco || 'Sem espaço';
        (acc[esp] = acc[esp] || []).push(img);
        return acc;
      }, {});

      let html = '';
      Object.entries(grupos).forEach(([espaco, imagens]) => {
        html += `<h5 class="mt-3">${espaco}</h5><div class="gallery-container">`;
        imagens.forEach(img => {
          const file = img.nome;
          const fileId = btoa(`${cod}_${nomeCampanha}_${file}`);
          html += `
            <div class="gallery-card" data-img="${fileId}">
              <img src="${img.url}" alt="${file}" class="gallery-img" />
              <div class="gallery-body">
                <div class="gallery-title">${file}</div>
                <a href="${img.url}" download class="gallery-btn">⬇️</a>
                <button class="btn btn-sm btn-danger mt-1"
                        onclick="deletarImagem('${cod}','${nomeCampanha}','${file}')">
                  🗑️
                </button>
              </div>
            </div>`;
        });
        html += '</div>';
      });

      html += `
        <hr>
        <h6>📤 Enviar novas fotos</h6>
        <input type="file" id="inputUploadFoto" multiple class="form-control mb-2">
        <button class="btn btn-primary" onclick="uploadFoto('${cod}', '${nomeCampanha}', document.getElementById('inputUploadFoto').files)">Enviar</button>
      `;

      $('#galeriaContainer').html(html);
    })
    .catch(err => {
      console.error('[abrirGaleria] erro no fetch ➞', err);
      $('#galeriaContainer').html(`
        <div class="alert alert-danger">
          Ocorreu um erro ao carregar as imagens. Tente novamente mais tarde.
        </div>
      `);
    });
}

function deletarImagem(cod, nomeCampanha, imagem) {
  if (!confirm("Tem certeza que deseja apagar esta imagem?")) return;

  const body = new URLSearchParams({
    cod,
    campanha: nomeCampanha,
    imagem
  });

  fetch(`${BASE}/deletar`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: body.toString()
  })
    .then(res => res.json())
    .then(data => {
      if (!data.success) {
        alert('❌ ' + data.mensagem);
        return;
      }
      alert(data.mensagem);
      const fileId = btoa(`${cod}_${nomeCampanha}_${imagem}`);
      $(`[data-img="${fileId}"]`).remove();
    })
    .catch(err => {
      console.error('[deletarImagem] erro na requisição ➞', err);
      alert("❌ Erro na requisição: " + err.message);
    });
}

function uploadFoto(cod, nomeCampanha, arquivos) {
  if (!cod || !nomeCampanha || !arquivos || arquivos.length === 0) {
    alert("Preencha todos os campos e selecione ao menos uma imagem.");
    return;
  }

  const formData = new FormData();
  formData.append('cod', cod);
  formData.append('nome', nomeCampanha);

  for (let i = 0; i < arquivos.length; i++) {
    formData.append('imagem', arquivos[i]);
  }

  fetch(`${BASE}/foto`, {
    method: 'POST',
    body: formData
  })
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        alert(data.mensagem || "Imagens enviadas com sucesso!");
        abrirGaleria(cod, nomeCampanha);
      } else {
        alert("❌ Erro ao enviar: " + (data.mensagem || "Erro desconhecido."));
      }
    })
    .catch(err => {
      console.error('[uploadFoto] erro na requisição ➞', err);
      alert("❌ Erro ao enviar imagens: " + err.message);
    });
}