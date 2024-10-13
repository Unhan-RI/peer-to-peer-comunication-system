import socket
import threading
import os
import time

# Daftar peer di jaringan
PEERS = [('192.168.0.110', 5001), ('192.168.0.109', 5002)]

# Fungsi untuk memindai direktori
def scan_files(base_dir='shared_files'):
    shared_files = {}
    for root, _, files in os.walk(base_dir):
        for file in files:
            file_path = os.path.join(root, file)
            shared_files[file] = file_path  # Simpan path absolut untuk setiap file
    return shared_files

# Fungsi untuk menjalankan server pada setiap node
def run_server(host, port, shared_files):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))  # Bind ke IP dan port node ini
    server_socket.listen(5)
    print(f"Node running as server on {host}:{port}")

    while True:
        conn, addr = server_socket.accept()
        threading.Thread(target=handle_client, args=(conn, addr, shared_files)).start()

# Fungsi untuk menangani permintaan dari client
def handle_client(conn, addr, shared_files):
    print(f"Connected by {addr}")
    data = conn.recv(1024).decode()
    command, filename = data.split(':')

    if command == "SEARCH":
        if filename in shared_files:
            conn.sendall(f"FOUND:{filename}:{addr}".encode())  # Kirim lokasi file
        else:
            conn.sendall("NOT_FOUND".encode())

    elif command == "GET":
        if filename in shared_files:
            with open(shared_files[filename], 'rb') as f:
                conn.sendall(f"FILE_SIZE:{os.path.getsize(shared_files[filename])}".encode())
                time.sleep(1)  # Menunggu sebelum mulai mengirim
                while True:
                    chunk = f.read(1024)
                    if not chunk:
                        break
                    conn.sendall(chunk)
            print(f"File '{filename}' sent to {addr}")
        else:
            conn.sendall("FILE_NOT_FOUND".encode())

    conn.close()

# Fungsi untuk mencari file dengan flooding ke semua peer (menambahkan pengukuran latensi dan response time)
def search_file(filename):
    start_time = time.time()  # Mulai pengukuran waktu
    for peer in PEERS:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(peer)
                s.sendall(f"SEARCH:{filename}".encode())
                response = s.recv(1024).decode()

                if response.startswith("FOUND"):
                    end_time = time.time()  # Akhiri pengukuran waktu
                    _, found_filename, addr = response.split(':')
                    latency = end_time - start_time
                    print(f"File '{found_filename}' found at {peer}")
                    print(f"Search Latency: {latency:.4f} seconds")
                    return peer

        except ConnectionRefusedError:
            print(f"Cannot connect to {peer}")

    end_time = time.time()
    print(f"File '{filename}' not found in the network.")
    response_time = end_time - start_time
    print(f"Search Response Time: {response_time:.4f} seconds")
    return None  # Return None if no peer has the file

# Fungsi untuk mengunduh file dari peer (menambahkan pengukuran throughput dan waktu unduhan)
def get_file(peer, filename):
    start_time = time.time()  # Mulai pengukuran waktu
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect(peer)
        s.sendall(f"GET:{filename}".encode())
        response = s.recv(1024).decode()

        if response.startswith("FILE_SIZE"):
            _, size = response.split(':')
            size = int(size)
            print(f"Receiving file '{filename}' from {peer} of size {size} bytes...")

            with open(f"downloaded_{filename}", 'wb') as f:
                bytes_received = 0
                while bytes_received < size:
                    data = s.recv(1024)
                    if not data:
                        break
                    f.write(data)
                    bytes_received += len(data)

            end_time = time.time()  # Akhiri pengukuran waktu
            duration = end_time - start_time
            throughput = size / duration  # Throughput in bytes per second
            print(f"File '{filename}' downloaded successfully.")
            print(f"Download Time: {duration:.4f} seconds")
            print(f"Throughput: {throughput:.2f} bytes/second")

        else:
            print("File not found on the peer.")

# Fungsi utama untuk menjalankan node
def run_node(host, port):
    shared_files = scan_files()  # Pindai file yang tersedia di direktori lokal

    threading.Thread(target=run_server, args=(host, port, shared_files)).start()

    time.sleep(1)  # Tunggu sebentar agar server siap menerima koneksi

    # Interactive menu
    while True:
        print("\nMenu:")
        print("1. Search for a file")
        print("2. Download a file")
        print("3. Exit")
        choice = input("Enter your choice: ")

        if choice == '1':
            filename = input("Enter the name of the file to search: ")
            search_file(filename)  # Call search function
        elif choice == '2':
            filename = input("Enter the name of the file to download: ")
            peer = search_file(filename)
            if peer:
                get_file(peer, filename)  # Download file from found peer

        elif choice == '3':
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please try again.")

# Jalankan node
if __name__ == "__main__":
    run_node('192.168.0.110', 5001)
