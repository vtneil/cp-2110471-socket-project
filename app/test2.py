from app.lib import AppGUI

if __name__ == "__main__":
    client_name = input('Input name: ')

    try:
        with AppGUI(client_name=client_name,
                    remote_host='chat.vt.in.th',
                    remote_port=50000) as app:
            app.run()

    except ConnectionError as e:
        print(f'Connection error: {e}, exiting...')
