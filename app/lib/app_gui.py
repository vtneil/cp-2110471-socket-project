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
        # yield JoinGroup()


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
    pressed_chatName = reactive('default is here',always_update=True)

    BINDINGS = [
        ('r', 'add_chatbox', "Refresh list on group/clients")
    ]

    def __init__(self, agent):
        super().__init__()
        self.agent = agent
        self.all_cli = self.agent.get_groups()[1]
        self.pinned_chat = []
        self.current_chat = None
        self.current_chat_type = None

    def compose(self):
        with ScrollableContainer(id='chatList'):
            yield ChatBox(gname="default",chat_type='c',agent=self.agent)

    def action_add_chatbox(self):
        chatboxes = self.query(ChatBox)
        if chatboxes :
            chatboxes.remove()
        container = self.query_one("#chatList")
        chatboxes = []
        pinned_chatboxes = []
        for i,c in enumerate(self.agent.get_groups()[1]):
            gname = "(GROUP) "+c
            chatbox = ChatBox(gname=gname , chat_type='g' , agent=self.agent)
            if gname in self.pinned_chat:
                chatbox.gname = '(Pin'+chatbox.gname[1:]
                pinned_chatboxes.append(chatbox)
            else:
                chatboxes.append(chatbox)
            # container.mount(chatbox)
        for i,c in enumerate(self.agent.get_connected_clients()[1]):
            gname = "(CLIENT) "+c
            chatbox = ChatBox(gname=gname , chat_type='c' , agent=self.agent)
            if gname in self.pinned_chat:
                chatbox.gname = '(Pin'+chatbox.gname[1:]
                pinned_chatboxes.append(chatbox)
            else:
                chatboxes.append(chatbox)
            # container.mount(chatbox) 
        for i in pinned_chatboxes:
            container.mount(i)
        for i in chatboxes:
            container.mount(i)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Event handler called when a button is pressed."""
        button_id = event.button.id
        button_name = event.button.name
        if button_id == "startChat":
            # button.startChat()
            if button_name.split()[2] == 'g':
                if self.agent.join_group(group_name = button_name.split()[1].strip(' ')) == MessageProtocolResponse.OK:
                    self.pressed_chatName = button_name.split()[1]
                    self.current_chat = button_name.split()[1].strip(' ')
                    self.current_chat_type = 'g'
                    print('In to chat group',self.pressed_chatName)
            else:
                self.pressed_chatName = button_name.split()[1]
                self.current_chat = button_name.split()[1].strip(' ')
                self.current_chat_type = 'c'
        else:
            button_name = event.button.name
            self.pinned_chat.append(button_name)
            self.action_add_chatbox()


class ChatBox(Static):

    pressed_chatName = reactive('default chat name')

    def __init__(self , gname = 'Default group name' ,chat_type = '',agent = None):
        super().__init__()
        self.gname = gname
        self.chat_type = chat_type
        self.agent = agent

    def compose(self):
        yield Label(self.gname, id='chatBoxName')
        yield Box(self.gname , self.chat_type)
    
    def get_chatName(self):
        return self.gname


class Box(Static):
    def __init__(self,gname,chat_type):
        super().__init__()
        self.gname = gname
        self.chat_type = chat_type

    def compose(self):
        yield Button(label='chat',name=self.gname+' '+self.chat_type, id='startChat')
        yield Button(label='pin',name=self.gname, id='pinChat')



class Bottom(Static):
    def compose(self):
        with ScrollableContainer(id='announcementList'):
            yield Announcement()
        yield Broadcast()
    
    # @on(Button.Pressed , '#broadCastButton')
    # def setAccounce(self):
    #     container = self.query_one('#announcementList')
    #     container.mount(Announcement(label=self.query_one(Broadcast).broadcastMessage))

class Announcement(Static):
    def __init__(self,label ='announcement text' ):
        super().__init__()
        self.label = label
        
    def compose(self):
        yield Label(self.label, id='announcementBox')


class Broadcast(Static):
    broadcastMessage = reactive('')
    # def __init__(self):
    #     super().__init__();
    def compose(self):
        yield Input(id='broadCastInput', classes='topInput')
        yield Button('broadcast', id='broadCastButton', classes='topButton')
# !======================================================================================

# ! ============================= Right side =============================================
# chat_name = 'Talk Arai U Dai'


class Right(Static):
    BINDINGS = [
        ('e' , 'refresh_right' , 'To Refresh Right')
    ]
    chat_name = reactive('default',recompose=True)
    def __init__(self,
                 m_buffer: MessageInfoDict,
                 g_buffer: MessageInfoDict,
                 src: tuple[str | None, str | None],
                 chatname):
        super().__init__()
        self.m_buffer = m_buffer
        self.g_buffer = g_buffer
        self.src = src
        self.chatname = chatname

    def compose(self) -> ComposeResult:
        # yield Label('wee')
        yield ChatName(self.chat_name)

        with ScrollableContainer(id='chat'):
            if self.src[1] in self.m_buffer:
                for message_info in self.m_buffer[self.src[1]]:
                    yield MessageBox(
                        sender=message_info.sender,
                        message=message_info.body
                    )
            elif self.src[0] in self.g_buffer:
                for message_info in self.g_buffer[self.src[0]]:
                    yield MessageBox(
                        sender=message_info.sender,
                        message=message_info.body
                    )

        yield InputText()
        yield Footer()


# TODO give Title of chatroom
class ChatName(Static):
    def __init__(self,chat_name):
        super().__init__()
        self.chat_name = chat_name

    def compose(self):
        yield Label(self.chat_name, id='chatName')
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
    message_to_send = reactive("")
    def compose(self):
        yield Input(placeholder='text something...', id='textBox')
        yield Button('send', variant='primary', id='sendButton')
        yield Button('send file', variant='primary', id='sendFileButton')


# ! ============================ Control center ==========================================
class AppGUI(App):

    BINDINGS = [
        ('r','refresh_announce','Refresh Announce')
    ]
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

        self.message_to_send = ''
        self.groupName = ''
        self.chatname=''

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

        elif self.src[1]:
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
                announce_msg = f'[{datetime_fmt()}] {message.src.username}: {message.body}'

                self.buffer.announcement.append(announce_msg)
                print(announce_msg)
                self.refresh_annoucement()

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
        if (self.src[0]): self.agent.leave_group(self.src[0])
        self.src = (None, recipient)
        return 0

    def compose(self):
        yield Header()
        yield Footer()
        yield Left(self.agent)
        yield Right(m_buffer=self.buffer.private,
                    g_buffer=self.buffer.group,
                    src=self.src,
                    chatname=self.chatname)
    def action_refresh_announce(self):
        self.refresh_annoucement()
        self.refresh_chat_messages()

    def refresh_chat_messages(self):
        chat_container = self.query_one("#chat")
        chat_container.remove_children('*')
        if self.src[1] in self.buffer.private:
            for message_info in self.buffer.private[self.src[1]]:
                new_message = MessageBox(sender=message_info.sender, message=message_info.body)
                chat_container.mount(new_message)
        elif self.src[0] in self.buffer.group:
            for message_info in self.buffer.group[self.src[0]]:
                new_message = MessageBox(sender=message_info.sender, message=message_info.body)
                chat_container.mount(new_message)
        chat_container.scroll_end()
    
    def refresh_annoucement(self):
        ann_container = self.query_one("#announcementList")
        ann_container.remove_children('*')
        for message_info in self.buffer.announcement:
            new_message = Announcement(label=message_info)
            ann_container.mount(new_message)
        ann_container.scroll_end()

    @on(Button.Pressed, '#switch')
    def switch(self):
        # self.agent.send_private('vt', 'safgsfgdjshf')
        self.dark = not self.dark

        #///////////for test purpose only //////////////
        # if self.client_name == 'a':
        #     self.chat('b')
        # if self.client_name == 'b':
        #     self.chat('a')
        #///////////for test purpose only //////////////

        # chat_container = self.query_one("#chat")
        # if self.src[1]:
        #     new_message = MessageBox(sender='HIII', message='HIII')
        #     chat_container.mount(new_message)

    @on(Input.Changed, '#textBox') 
    def textInputHandler(self,event:Input.Changed) -> None :
        self.query_one(InputText).message_to_send = event.value
        self.message_to_send = self.query_one(InputText).message_to_send

    @on(Button.Pressed, '#sendButton')
    def action_add_message(self) -> None:
        # self.message_to_send = str(self.src[0])
        # if self.src[0] in self.buffer.group.keys():
        #     self.message_to_send = self.buffer.group[self.src[0]]
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

    @on(Button.Pressed, '#sendFileButton')
    def action_add_file(self) -> None:
        if os.path.isfile(self.message_to_send):
            with open(self.message_to_send, mode='rb') as f:
                file_content: bytes = f.read()
                file_proto = new_file_proto(filename=os.path.basename(self.message_to_send),
                                            content=file_content)
                if self.src[0]:
                    self.agent.send_group(group_name=self.src[0],
                                        data_type=MessageProtocolCode.DATA.FILE,
                                        data=file_proto)
                    self.store_chat(
                        self.src[0],
                        MessageInfo(
                            sender=f'You {datetime_fmt()}',
                            body=f'Sent a file'
                        )
                    )

                else:
                    self.agent.send_private(recipient=self.src[1],
                                            data_type=MessageProtocolCode.DATA.FILE,
                                            data=file_proto)
                    self.store_chat(
                        self.src[1],
                        MessageInfo(
                            sender=f'You {datetime_fmt()}',
                            body=f'Sent a file'
                        )
                    )
            self.refresh_chat_messages()
            return 0
        else:
            logger.error(f'File {self.message_to_send} doesn\'t exist!')
            return 1

    #create Group
    @on(Input.Changed , '#createGroupInput')
    def groupNameHandler(self,event:Input.Changed) -> None:
        self.query_one(CreateGroup).groupname = event.value
    @on(Button.Pressed , '#createGroupButton')
    def createGroup(self):
        log('create button was pressed')
        if self.agent.create_group(group_name=self.query_one(CreateGroup).groupname) == MessageProtocolResponse.OK :
            print("GroupName",self.query_one(CreateGroup).groupname)
    
    #Annouce broadcast
    @on(Input.Changed , '#broadCastInput')
    def annouceHandler(self,event:Input.Changed) -> None:
        self.query_one(Broadcast).broadcastMessage = event.value
    
    @on(Button.Pressed , '#broadCastButton')
    def sendAnnouce(self):
        log('broadcast button was pressed')
        self.agent.announce(data=self.query_one(Broadcast).broadcastMessage)
        container = self.query_one('#announcementList')
        # container.mount(Announcement(label=self.query_one(Broadcast).broadcastMessage))
        self.buffer.announcement.append(self.query_one(Broadcast).broadcastMessage)
        self.refresh_annoucement()
    def on_mount(self) -> None:
        def update_chatname(new_chatname:str) ->None:
            log('pressed chatnamae =',new_chatname)
            self.query_one(Right).chat_name = new_chatname
        self.watch(self.query_one(Middle) , 'pressed_chatName' , update_chatname)

    @on(Button.Pressed, '#startChat')
    def startChat(self):
        current_chat = self.query_one(Middle).current_chat
        chat_type = self.query_one(Middle).current_chat_type
        if chat_type == 'g':
            self.src = (current_chat,None)
        else:
            self.chat(recipient=current_chat)


    # ===== Context manager ===== #

    def __enter__(self):
        logger.info('Setting up GUI app for you...')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        logger.info('Closing GUI app...')
        self.agent.stop()