# A importação da classe 'SocketIO' não é mais necessária aqui
from flask_socketio import disconnect, join_room

# <<< CORREÇÃO CRÍTICA >>>
# Em vez de criar um novo SocketIO, importamos a instância 'socketio'
# que já foi criada no arquivo __init__.py
from . import socketio 

@socketio.on('connect')
def on_ws_connect(auth):
    """
    Handler para quando um cliente se conecta via WebSocket.
    Verifica a autenticação e adiciona o usuário a uma sala privada.
    """
    usuario = auth.get("usuario") if auth else None
    if not usuario:
        print("❌ WS desconectado: autenticação não fornecida.")
        disconnect()  # Desconecta o cliente se não houver autenticação
    else:
        print(f"✅ WS conectado por: {usuario}")
        join_room(usuario) # Coloca o cliente em uma sala com seu próprio nome de usuário

def notificar_usuario(usuario, dados):
    """
    Função auxiliar para enviar uma notificação para um usuário específico.
    Pode ser importada e usada em qualquer outra parte da aplicação (ex: rotas Flask).
    """
    # Esta função agora usa a instância correta e conectada do socketio
    socketio.emit("nova_campanha", dados, room=usuario)