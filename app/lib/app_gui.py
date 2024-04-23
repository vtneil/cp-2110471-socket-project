import dataclasses
import os
import threading
import time
from collections import defaultdict

from textual import on, events, log
from textual.app import App, ComposeResult
from textual.reactive import reactive
from textual.containers import ScrollableContainer, Horizontal
from textual.widgets import Footer, Header, Button, Static, Placeholder, Input, Pretty, Label, RichLog, Switch
from textual.color import Color
from textual.containers import Container

from app.common import *
from app.common.client import *
from app.common.types import *


# !================================================================================


@dataclasses.dataclass(init=True, repr=True, order=True)
class MessageInfo:
    sender: str
    body: str


MessageInfoDict = defaultdict[str, list[MessageInfo]]


@dataclasses.dataclass(init=True, repr=True, order=True)
class MessageInfoBuffer:
    private: MessageInfoDict = dataclasses.field(default_factory=MessageInfoDict)
    group: MessageInfoDict = dataclasses.field(default_factory=MessageInfoDict)
    announcement: list[str] = dataclasses.field(default_factory=list[str])


# ! ============================== Left side =============================================
class Left(Static):
    BINDINGS = [
        ('r', 'add_chatbox', "Refresh list on group/clients")
    ]

    def __init__(self, agent):
        super().__init__()
        self.agent = agent

    def compose(self):
        yield Top()
        yield Middle(self.agent)
        yield Bottom()
        yield Footer()


class Top(Static):
    def compose(self):
        yield CreateGroup()
        yield JoinGroup()


class CreateGroup(Static):
    groupname = reactive("")

    def compose(self):
        yield Input(id='createGroupInput', classes='topInput')
        yield Button('create group', id='createGroupButton', classes='topButton')


class JoinGroup(Static):
    groupname = reactive("")

    def compose(self):
        yield Input(id='joinGroupInput', classes='topInput')
        yield Button('join group', id='joinGroupButton', classes='topButton')


class Middle(Static):
    BINDINGS = [
        ('r', 'add_chatbox', "Refresh list on group/clients")
    ]

    def __init__(self, agent):
        super().__init__()
        self.agent = agent
        self.all_cli = self.agent.get_groups()[1]

    def compose(self):
        with ScrollableContainer(id='chatList'):
            yield ChatBox(gname="default")

    def action_add_chatbox(self):
        chatboxes = self.query(ChatBox)
        if chatboxes:
            chatboxes.remove()
        container = self.query_one("#chatList")
        for i, c in enumerate(self.agent.get_groups()[1]):
            chatbox = ChatBox(gname=c)
            container.mount(chatbox)


class ChatBox(Static):
    def __init__(self, gname):
        super().__init__()
        self.gname = gname

    def compose(self):
        yield Label(self.gname, id='chatBoxName')
        yield Box()


class Box(Static):
    def compose(self):
        yield Button('chat', id='startChat')
        yield Button('pin', id='pinChat')


class Bottom(Static):
    def compose(self):
        with ScrollableContainer(id='announcementList'):
            yield Announcement()
            yield Announcement()
            yield Announcement()
            yield Announcement()
            yield Announcement()
            yield Announcement()
            yield Announcement()
        yield Broadcast()


class Announcement(Static):
    def compose(self):
        yield Label('announcement text', id='announcementBox')


class Broadcast(Static):
    def compose(self):
        yield Input(id='broadCastInput', classes='topInput')
        yield Button('broadcast', id='broadcastButton', classes='topButton')


# !======================================================================================

# ! ============================= Right side =============================================
chat_name = 'Talk Arai U Dai'


class Right(Static):
    def __init__(self,
                 m_buffer: MessageInfoDict,
                 g_buffer: MessageInfoDict,
                 src: tuple[str | None, str | None]):
        super().__init__()
        self.m_buffer = m_buffer
        self.g_buffer = g_buffer
        self.src = src

    def compose(self) -> ComposeResult:
        # yield Label('wee')
        yield ChatName()

        with ScrollableContainer(id='chat'):
            if self.src[1] in self.m_buffer:
                for message_info in self.m_buffer[self.src[1]]:
                    yield MessageBox(
                        sender=message_info.sender,
                        message=message_info.body
                    )

        yield InputText()
        yield Footer()


# TODO give Title of chatroom
class ChatName(Static):
    def compose(self):
        yield Label(chat_name, id='chatName')
        yield Button('switch', id='switch')
        # * switch mode (dark-light)


class MessageBox(Static):
    def __init__(self, sender, message, **kwargs):
        super().__init__(**kwargs)
        self.sender = sender
        self.message = message

    def compose(self):
        yield Label(self.sender)
        yield Label(self.message, classes='message')


class SwitchMode(Static):
    def compose(self):
        yield Button('switch', id='switch')
        # yield Horizontal(
        #     Static("off:     ", classes="label"),
        #     Switch(animate=False),
        #     classes="container",
        # )


# * Input message and send Button div
# TODO apply send message function
class InputText(Static):
    def compose(self):
        yield Input(placeholder='text something...', id='textBox')
        yield Button('send', variant='primary', id='sendButton')
        yield Button('send file', variant='primary', id='sendFileButton')


# ! ============================ Control center ==========================================
class AppGUI(App):
    CSS_PATH = 'chat.tcss'

    def __init__(self,
                 client_name: str,
                 remote_host: str,
                 remote_port: int):
        super().__init__()

        self.client_name: str = client_name

        self.agent = ChatAgent(
            client_name=self.client_name,
            remote_address=(remote_host, remote_port),
            open_sockets=4,
            recv_callback=self.on_receive,
            disc_callback=None
        )

        self.message_to_send = 'asfasf'
        self.groupName = ''

        self.recv_count = 0

        self.local_clients: dict[str, tuple[float, tuple[str, int]]] = {}
        self.local_servers: dict[str, tuple[float, tuple[str, int]]] = {}

        self.src: tuple[str | None, str | None] = (None, None)

        # Buffers
        self.buffer: MessageInfoBuffer = MessageInfoBuffer()

        # Success message
        #

    def store_chat(self, chatroom: str, *message_infos: MessageInfo):
        if self.src[0]:
            # Group message
            if self.src[0] not in  self.buffer.group.keys():
                self.buffer.group[self.src[0]] = list()
            self.buffer.group[self.src[0]].extend(message_infos)

        else:
            # Private message
            if self.src[1] not in  self.buffer.private.keys():
                self.buffer.private[self.src[1]] = list()
            self.buffer.private[self.src[1]].extend(message_infos)

    def on_receive(self, message: MessageProtocol):
        self.recv_count = self.recv_count + 1

        if not validate_message(message):
            return

        # self.agent.send_private(
        #     recipient='vt1',
        #     data_type=MessageProtocolCode.DATA.PLAIN_TEXT,
        #     data=f'{message}'
        # )

        # self.agent.send_private(
        #     recipient='vt',
        #     data_type=MessageProtocolCode.DATA.PLAIN_TEXT,
        #     data=f'{message}'
        # )

        if message.message_type == MessageProtocolCode.DATA.FILE:
            # Receive file
            _file_proto: FileProtocol = message.body

            print(f'[{datetime_fmt()}] {message.src.username}: '
                  f'Sent a file: {_file_proto.filename} '
                  f'(size: {_file_proto.size} bytes)')

            # Save file
            home_dir = os.path.expanduser("~").replace('\\', '/')
            filename = uniquify(f'{home_dir}/Downloads/socket/{_file_proto.filename}')
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            with open(filename, mode='wb') as f:
                f.write(_file_proto.content)

            if self.src[0]:
                self.store_chat(
                    self.src[0],
                    MessageInfo(
                        sender=f'{message.src.username} {datetime_fmt()}',
                        body=f'SENT A {_file_proto.size} bytes FILE to \"{filename}\".'
                    )
                )
            else:
                self.store_chat(
                    self.src[1],
                    MessageInfo(
                        sender=f'{message.src.username} {datetime_fmt()}',
                        body=f'SENT A {_file_proto.size} bytes FILE to \"{filename}\".'
                    )
                )

            logger.info(f'File {_file_proto.filename} is saved as \"{filename}\".')

        else:
            # Other formats
            if message.message_flag and message.message_flag == MessageProtocolFlag.ANNOUNCE:
                announce_msg = f'[{datetime_fmt()}] Announcement from {message.src.username}: {message.body}'

                self.buffer.announcement.append(announce_msg)
                print(announce_msg)

            else:
                if self.src[0]:
                    self.store_chat(
                        self.src[0],
                        MessageInfo(
                            sender=f'{message.src.username} {datetime_fmt()}',
                            body=f'{message.body}'
                        )
                    )

                else:
                    self.store_chat(
                        self.src[1],
                        MessageInfo(
                            sender=f'{message.src.username} {datetime_fmt()}',
                            body=f'{message.body}'
                        )
                    )

                print(f'[{datetime_fmt()}] {message.src.username}: {message.body}')

        self.refresh_chat_messages()

    def on_discovery(self, message: MessageProtocol):
        if not validate_message(message):
            return

        logger.info(f'I discovered something!: {message}')

        # Adding
        if message.message_type == MessageProtocolCode.INSTRUCTION.BROADCAST.SERVER_DISC:
            self.local_servers[message.src.username] = time.time(), message.src.address
        elif message.message_type == MessageProtocolCode.INSTRUCTION.BROADCAST.CLIENT_DISC:
            self.local_clients[message.src.username] = time.time(), message.src.address
        else:
            return

        # Cleanup
        tim_callback = time.time()
        for server in list(self.local_servers.keys()):
            if tim_callback - self.local_servers[server][0] >= 5.0:
                self.local_servers.pop(server)
        for client in list(self.local_clients.keys()):
            if tim_callback - self.local_clients[client][0] >= 5.0:
                self.local_clients.pop(client)

    def chat(self, recipient):
        self.src = (None, recipient)
        return 0

    def compose(self):
        yield Header()
        yield Footer()
        yield Left(self.agent)
        yield Right(m_buffer=self.buffer.private,
                    g_buffer=self.buffer.group,
                    src=self.src)

    def refresh_chat_messages(self):
        chat_container = self.query_one("#chat")
        chat_container.remove_children('*')
        if self.src[1] in self.buffer.private:
            for message_info in self.buffer.private[self.src[1]]:
                new_message = MessageBox(sender=message_info.sender, message=message_info.body)
                chat_container.mount(new_message)
        chat_container.scroll_end()

    @on(Button.Pressed, '#switch')
    def switch(self):
        # self.agent.send_private('vt', 'safgsfgdjshf')
        self.dark = not self.dark

        if self.client_name == 'p':
            self.chat('g')
        if self.client_name == 'g':
            self.chat('p')

        chat_container = self.query_one("#chat")
        if self.src[1]:
            new_message = MessageBox(sender='HIII', message='HIII')
            chat_container.mount(new_message)

    @on(Button.Pressed, '#sendButton')
    def action_add_message(self) -> None:
        self.message_to_send = str(self.recv_count)
        if self.src[0]:
            self.agent.send_group(group_name=self.src[0],
                                  data_type=MessageProtocolCode.DATA.PLAIN_TEXT,
                                  data=self.message_to_send)
            self.store_chat(
                self.src[0],
                MessageInfo(
                    sender=f'You {datetime_fmt()}',
                    body=f'{self.message_to_send}'
                )
            )

        else:
            self.agent.send_private(recipient=self.src[1],
                                    data_type=MessageProtocolCode.DATA.PLAIN_TEXT,
                                    data=self.message_to_send)
            self.store_chat(
                self.src[1],
                MessageInfo(
                    sender=f'You {datetime_fmt()}',
                    body=f'{self.message_to_send}'
                )
            )

        self.refresh_chat_messages()

    # create Group
    @on(Input.Changed, '#createGroupInput')
    def groupNameHandler(self, event: Input.Changed) -> None:
        self.query_one(CreateGroup).groupname = event.value

    @on(Button.Pressed, '#createGroupButton')
    def createGroup(self):
        if self.agent.create_group(group_name=self.query_one(CreateGroup).groupname) == MessageProtocolResponse.OK:
            print("GroupName", self.query_one(CreateGroup).groupname)

    # ===== Context manager ===== #

    def __enter__(self):
        logger.info('Setting up GUI app for you...')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        logger.info('Closing GUI app...')
        self.agent.stop()
