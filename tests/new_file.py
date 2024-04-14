import os


def create_random_binary_file(filename: str, size: int):
    random_data = os.urandom(size)

    with open(filename, 'wb') as f:
        f.write(random_data)
    print(f"Created file '{filename}' with size {size} bytes.")


if __name__ == '__main__':
    create_random_binary_file(
        filename='../rand/2mb.bin',
        size=2_000_000
    )
