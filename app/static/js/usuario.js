$(document).ready(function() {
    
    // --- 1. Preencher o Modal ao Clicar em Editar ---
    $('.btn-editar-usuario').on('click', function() {
        const userId = $(this).data('id');
        const username = $(this).data('username');

        // Preenche os campos do Modal
        $('#editUserId').val(userId);
        $('#editUsername').val(username);
        $('#currentUsername').text(username);
        
        // Limpa os campos de senha sempre que o modal é aberto
        $('#editPassword').val('');
        $('#editConfirmPassword').val('');
    });

    // --- 2. Enviar a Requisição de Edição ---
    $('#btnSalvarEdicao').on('click', async function() {
        const userId = $('#editUserId').val();
        const username = $('#editUsername').val();
        const password = $('#editPassword').val();
        const confirmPassword = $('#editConfirmPassword').val();
        
        // Validação de senhas
        if (password !== confirmPassword) {
            alert("A nova senha e a confirmação de senha não coincidem.");
            return;
        }

        const data = {
            user_id: userId,
            username: username
        };
        
        // Inclui a senha apenas se ela foi preenchida
        if (password.trim() !== "") {
            data.password = password;
        }

        try {
            const response = await fetch(`/api/user/${userId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (response.ok) {
                alert("✅ Usuário atualizado com sucesso!");
                $('#modalEdicaoUsuario').modal('hide');
                // Recarrega a página para refletir as alterações na tabela
                window.location.reload(); 
            } else {
                alert(`❌ Erro ao atualizar usuário: ${result.message || 'Erro desconhecido'}`);
            }
        } catch (error) {
            console.error('Erro de rede:', error);
            alert("❌ Erro de comunicação com o servidor.");
        }
    });
});