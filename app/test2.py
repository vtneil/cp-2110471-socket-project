import os
import time
from textual import on, events
from textual.app import App, ComposeResult
from textual.reactive import reactive
from textual.containers import ScrollableContainer, Horizontal
from textual.widgets import Footer, Header, Button, Static, Placeholder, Input, Pretty, Label, RichLog, Switch
from textual.color import Color
from textual.containers import Container

from app.common import *
from app.common.client import *


# ! ============================== Left side =============================================
class Left(Static):
    BINDINGS = [
        ('r','add_chatbox',"Refresh list on group/clients")
    ]
    def __init__(self,agent):
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
        ('r','add_chatbox',"Refresh list on group/clients")
    ]
    def __init__(self,agent):
        super().__init__()
        self.agent = agent
        self.all_cli = self.agent.get_groups()[1]

    def compose(self):
        with ScrollableContainer(id='chatList'):
            yield ChatBox(gname="default")

    def action_add_chatbox(self):
        chatboxes = self.query(ChatBox)
        if chatboxes :
            chatboxes.remove()
        container = self.query_one("#chatList")
        for i,c in enumerate(self.agent.get_groups()[1]):
            chatbox = ChatBox(gname=c)
            container.mount(chatbox)

class ChatBox(Static):
    def __init__(self , gname):
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
    def __init__(self,m_buffer,g_buffer,src):
        super().__init__()
        self.m_buffer = m_buffer
        self.g_buffer = g_buffer
        self.src = src

    def compose(self) -> ComposeResult:
        # yield Label('wee')
        yield ChatName()
        with ScrollableContainer(id='chat') :
            if (self.src[1] in self.m_buffer.keys()):
                for message_info in self.m_buffer[self.src[1]]:
                    yield MessageBox(sender=message_info.sender
                                     ,message=message_info.body)
        yield InputText()
        yield Footer()


# TODO give Title of chatroom
class ChatName(Static):
    def compose(self):
        yield Label(chat_name, id='chatName')
        yield Button('switch', id='switch')
        # * switch mode (dark-light)


class MessageBox(Static):
    def __init__(self, sender,message, **kwargs):
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


# !================================================================================

class message_info:
    def __init__(self, sender, body):
        self.sender = sender
        self.body = body

# ! ============================ Control center ==========================================
class ChatApp(App):
    CSS_PATH = 'chat.tcss'
    def __init__(self, remote_host: str, remote_port: int):
        super().__init__()
        self.agent = ChatAgent(client_name,
                               (remote_host, remote_port),
                               4,
                               recv_callback=self.on_receive
                               )
        self.mes = 'asfasf'
        self.groupName = ''

        self.resv_call = 0

        self.local_clients: dict[str, tuple[float, tuple[str, int]]] = {}
        self.local_servers: dict[str, tuple[float, tuple[str, int]]] = {}


        self.src: tuple[str | None, str | None] = (None, None)
        # Buffers
        self.message_buffer = dict()
        self.group_message_buffer = dict()

    def store_chat_buffer(self,message_list,chatroom):
        if self.src[0]:
            if self.src[0] not in self.group_message_buffer.keys() :
                self.group_message_buffer[self.src[0]] = []
            self.group_message_buffer[self.src[0]].extend(message_list)
        else:
            if chatroom not in self.message_buffer.keys() :
                self.message_buffer[chatroom] = []
            self.message_buffer[chatroom].extend(message_list)


    def on_receive(self,message: MessageProtocol):
        self.resv_call = self.resv_call + 1
        if not isinstance(message, MessageProtocol) or not message.src:
            return
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
                self.store_chat_buffer([message_info(sender=f'{message.src.username} {datetime_fmt()}',
                                                body=f'SENT A {_file_proto.size} bytes FILE to \"{filename}\".')]
                                    ,self.src[0])
            else:
                self.store_chat_buffer([message_info(sender=f'{message.src.username} {datetime_fmt()}',
                                                body=f'SENT A {_file_proto.size} bytes FILE to \"{filename}\".')]
                                    ,self.src[1])
            logger.info(f'File {_file_proto.filename} is saved as \"{filename}\".')

        else:
            # Other format
            if message.message_flag and message.message_flag == MessageProtocolFlag.ANNOUNCE:
                self.announce_buffer.append(f'[{datetime_fmt()}] Announcement from {message.src.username}: {message.body}')
                print(f'[{datetime_fmt()}] Announcement from {message.src.username}: {message.body}')
            else:
                if self.src[0]:
                    self.store_chat_buffer([message_info(sender=f'{message.src.username} {datetime_fmt()}',body=f'{message.body}')],self.src[0])
                else :
                    self.store_chat_buffer([message_info(sender=f'{message.src.username} {datetime_fmt()}',body=f'{message.body}')],self.src[1])
                print(f'[{datetime_fmt()}] {message.src.username}: {message.body}')       
        self.refresh_chat_messages()
    def on_discovery(self, message: MessageProtocol):
        if not (message and isinstance(message, MessageProtocol)):
            return

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
        yield Right(m_buffer=self.message_buffer
                    ,g_buffer=self.group_message_buffer
                    ,src=self.src)
        
    def refresh_chat_messages(self):
        chat_container = self.query_one("#chat")
        chat_container.remove_children('*')
        if self.src[1] in self.message_buffer:
            for message_info in self.message_buffer[self.src[1]]:
                new_message = MessageBox(sender=message_info.sender, message=message_info.body)
                chat_container.mount(new_message)
        chat_container.scroll_end()

    @on(Button.Pressed, '#switch')
    def switch(self):
        # self.agent.send_private('vt', 'safgsfgdjshf')
        self.dark = not self.dark
        if (client_name=='p'):self.chat('g')
        if (client_name=='g'):self.chat('p')
        chat_container = self.query_one("#chat")
        if self.src[1]:
            new_message = MessageBox(sender='HIII', message='HIII')
            chat_container.mount(new_message)

    @on(Button.Pressed, '#sendButton')
    def action_add_message(self) -> None:
        self.mes = str(self.resv_call)
        if self.src[0]:
            self.agent.send_group(group_name=self.src[0],
                                    data_type=MessageProtocolCode.DATA.PLAIN_TEXT,
                                    data=self.mes)
            self.store_chat_buffer([message_info(sender=f'You {datetime_fmt()}',body=f'{self.mes}')],self.src[0])
        else:
            self.agent.send_private(recipient=self.src[1],
                                      data_type=MessageProtocolCode.DATA.PLAIN_TEXT,
                                      data=self.mes)
            self.store_chat_buffer([message_info(sender=f'You {datetime_fmt()}',body=f'{self.mes}')],self.src[1])
        self.refresh_chat_messages()

    #create Group
    @on(Input.Changed , '#createGroupInput')
    def groupNameHandler(self,event:Input.Changed) -> None:
        self.query_one(CreateGroup).groupname = event.value

    @on(Button.Pressed , '#createGroupButton')
    def createGroup(self):
        if self.agent.create_group(group_name=self.query_one(CreateGroup).groupname) == MessageProtocolResponse.OK :
            print("GroupName",self.query_one(CreateGroup).groupname)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.agent.stop()


if __name__ == "__main__":
    client_name = input('Input name: ')
    with ChatApp('localhost' , 50000) as app:
        app.run()