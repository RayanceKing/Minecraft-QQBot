from mcdreforged.api.types import PluginServerInterface
from websocket import WebSocketConnectionClosedException
from json import JSONDecodeError
import asyncio

from .Base import Websocket
from ..Config import Config
from ..Utils import decode, encode


class WebsocketSender(Websocket):
    def __init__(self, server: PluginServerInterface, config: Config):
        Websocket.__init__(self, server, config, 'bot')

    def send_data(self, event_type: str, data=None, wait_response: bool = True):
        message_data = {'type': event_type}
        if data is not None:
            message_data['data'] = data
        if not self.websocket:
            if not self.connect():
                self.server.logger.warning('与机器人服务器的连接已断开，无法发送数据！')
                return None
            self.server.logger.info('检测到连接关闭，已重新连接到机器人！')
        try:
            self.websocket.send(encode(message_data))
            self.server.logger.debug(f'发送 {message_data} 事件成功！')
            if not wait_response:
                return True
            self.server.logger.debug('等待来自机器人的回应……')
            response = decode(self.websocket.recv())
            self.server.logger.info(f'收到来自机器人的消息 {response}')
        except asyncio.TimeoutError:
            self.server.logger.warning('等待机器人回应超时！')
            self.websocket = None  # 重置 websocket 连接
            return None
        except (WebSocketConnectionClosedException, JSONDecodeError, ConnectionError):
            self.server.logger.warning('与机器人的连接已断开！正在尝试重连')
            self.websocket = None  # 重置 websocket 连接
            for _ in range(3):
                if self.connect():
                    self.send_data(event_type, data)
                    break 
        except Exception as e:
            self.server.logger.error(f'发送数据时发生未知错误: {e}')
            return None
        self.server.logger.debug(f'来自机器人的回应 {response}！')
        if response.get('success'):
            return response.get('data', True)
        self.server.logger.warning(f'向 WebSocket 服务器发送 {event_type} 事件失败！请检查机器人。')


    def send_player_chat(self, player: str, message: str):
        self.send_data('player_chat', (player, message), wait_response=False)

    def send_synchronous_message(self, message: str):
        self.server.logger.info(F'向 QQ 群发送消息 {message}')
        return self.send_data('message', message)

    def send_startup(self):
        if response := self.send_data('server_startup'):
            self.server.logger.info('发送服务器启动消息成功！')
            self.config.flag = response
            self.server.logger.info(F'保存同步的配置 {self.config}')
            self.server.save_config_simple(self.config)
            return None
        self.server.logger.error('发送服务器启动消息失败！请检查配置或查看是否启动服务端，然后重试。')
    
    def send_shutdown(self):
        if self.send_data('server_shutdown'):
            self.server.logger.info('发送服务器关闭消息成功！')
            return None
        self.server.logger.error('发送服务器关闭消息失败！请检查配置或查看是否启动服务端，然后重试。')

    def send_player_left(self, player: str):
        if self.send_data('player_left', player):
            self.server.logger.info(F'发送玩家 {player} 离开消息成功！')
            return None
        self.server.logger.error(F'发送玩家 {player} 离开消息失败！请检查配置或查看是否启动服务端，然后重试。')

    def send_player_joined(self, player: str):
        if self.send_data('player_joined', player):
            self.server.logger.info(F'发送玩家 {player} 加入消息成功！')
            return None
        self.server.logger.error(F'发送玩家 {player} 加入消息失败！请检查配置或查看是否启动服务端，然后重试。')
