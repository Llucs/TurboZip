#!/usr/bin/env python3
"""
TZP Encoder - Turbo Zip Compressor
Implementação do compressor para o formato .tzp (Turbo Zip)

Autor: Llucs
Versão: 1.0
"""

import os
import sys
import struct
import time
import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple, Optional, Dict, Any
import argparse

try:
    import lz4.block
    import zstandard as zstd
except ImportError as e:
    print(f"Erro: Bibliotecas de compressão não encontradas: {e}")
    print("Instale com: pip install lz4 zstandard")
    sys.exit(1)

# Constantes do formato TZP
TZP_MAGIC = 0x545A5000  # "TZP\0"
TZP_VERSION = 0x0100     # Versão 1.0
DEFAULT_BLOCK_SIZE = 1024 * 1024  # 1MB por bloco

# Algoritmos de compressão
ALGO_LZ4 = 0x00
ALGO_ZSTD = 0x01
ALGO_UNCOMPRESSED = 0xFF

# Flags
FLAG_PREPROCESSED = 0x0001
FLAG_ENCRYPTED = 0x0001
FLAG_FULL_CHECKSUM = 0x0002

class TZPBlock:
    """Representa um bloco de dados no formato TZP"""
    
    def __init__(self, data: bytes, block_id: int):
        self.block_id = block_id
        self.original_data = data
        self.original_size = len(data)
        self.compressed_data = None
        self.compressed_size = 0
        self.algorithm = ALGO_UNCOMPRESSED
        self.compression_level = 0
        self.flags = 0
        self.checksum = 0
        self.offset = 0
        
    def calculate_checksum(self) -> int:
        """Calcula checksum CRC32 dos dados originais"""
        import zlib
        return zlib.crc32(self.original_data) & 0xffffffff
    
    def compress_lz4(self) -> Tuple[bytes, int]:
        """Comprime o bloco usando LZ4"""
        try:
            compressed = lz4.block.compress(self.original_data, mode='fast')
            return compressed, len(compressed)
        except Exception as e:
            print(f"Erro na compressão LZ4 do bloco {self.block_id}: {e}")
            return self.original_data, self.original_size
    
    def compress_zstd(self, level: int = 3) -> Tuple[bytes, int]:
        """Comprime o bloco usando Zstandard"""
        try:
            cctx = zstd.ZstdCompressor(level=level)
            compressed = cctx.compress(self.original_data)
            return compressed, len(compressed)
        except Exception as e:
            print(f"Erro na compressão Zstd do bloco {self.block_id}: {e}")
            return self.original_data, self.original_size
    
    def find_best_compression(self) -> None:
        """Encontra a melhor compressão para este bloco"""
        # Testa LZ4 (rápido)
        lz4_data, lz4_size = self.compress_lz4()
        lz4_ratio = lz4_size / self.original_size if self.original_size > 0 else 1.0
        
        # Testa Zstd nível 3 (balanceado)
        zstd_data, zstd_size = self.compress_zstd(3)
        zstd_ratio = zstd_size / self.original_size if self.original_size > 0 else 1.0
        
        # Testa Zstd nível 6 (alta compressão) se o bloco for grande
        zstd_high_data, zstd_high_size = None, float('inf')
        if self.original_size > 64 * 1024:  # Só para blocos > 64KB
            zstd_high_data, zstd_high_size = self.compress_zstd(6)
        zstd_high_ratio = zstd_high_size / self.original_size if self.original_size > 0 else 1.0
        
        # Escolhe o melhor algoritmo baseado na taxa de compressão
        best_ratio = min(lz4_ratio, zstd_ratio, zstd_high_ratio, 1.0)
        
        # Se não há benefício significativo (< 5% de redução), não comprime
        if best_ratio > 0.95:
            self.compressed_data = self.original_data
            self.compressed_size = self.original_size
            self.algorithm = ALGO_UNCOMPRESSED
            self.compression_level = 0
        elif best_ratio == lz4_ratio:
            self.compressed_data = lz4_data
            self.compressed_size = lz4_size
            self.algorithm = ALGO_LZ4
            self.compression_level = 1
        elif best_ratio == zstd_ratio:
            self.compressed_data = zstd_data
            self.compressed_size = zstd_size
            self.algorithm = ALGO_ZSTD
            self.compression_level = 3
        else:  # zstd_high_ratio
            self.compressed_data = zstd_high_data
            self.compressed_size = zstd_high_size
            self.algorithm = ALGO_ZSTD
            self.compression_level = 6
        
        self.checksum = self.calculate_checksum()

class TZPEncoder:
    """Encoder principal para o formato TZP"""
    
    def __init__(self, block_size: int = DEFAULT_BLOCK_SIZE, num_threads: int = None):
        self.block_size = block_size
        self.num_threads = num_threads or min(8, os.cpu_count() or 1)
        self.blocks: List[TZPBlock] = []
        self.total_original_size = 0
        self.total_compressed_size = 0
        
    def split_into_blocks(self, data: bytes) -> List[TZPBlock]:
        """Divide os dados em blocos"""
        blocks = []
        block_id = 0
        
        for i in range(0, len(data), self.block_size):
            block_data = data[i:i + self.block_size]
            block = TZPBlock(block_data, block_id)
            blocks.append(block)
            block_id += 1
            
        return blocks
    
    def compress_block(self, block: TZPBlock) -> TZPBlock:
        """Comprime um bloco individual"""
        block.find_best_compression()
        return block
    
    def compress_file(self, input_path: str, output_path: str) -> Dict[str, Any]:
        """Comprime um arquivo para o formato TZP"""
        start_time = time.time()
        
        print(f"Comprimindo: {input_path} -> {output_path}")
        
        # Lê o arquivo de entrada
        try:
            with open(input_path, 'rb') as f:
                data = f.read()
        except IOError as e:
            raise Exception(f"Erro ao ler arquivo de entrada: {e}")
        
        self.total_original_size = len(data)
        print(f"Tamanho original: {self.total_original_size:,} bytes")
        
        # Calcula checksum do arquivo completo
        file_checksum = hashlib.sha256(data).digest()[:8]  # Primeiros 8 bytes do SHA256
        file_checksum_int = struct.unpack('<Q', file_checksum)[0]
        
        # Divide em blocos
        print(f"Dividindo em blocos de {self.block_size:,} bytes...")
        self.blocks = self.split_into_blocks(data)
        print(f"Total de blocos: {len(self.blocks)}")
        
        # Comprime blocos em paralelo
        print(f"Comprimindo blocos usando {self.num_threads} threads...")
        with ThreadPoolExecutor(max_workers=self.num_threads) as executor:
            # Submete todos os blocos para compressão
            future_to_block = {executor.submit(self.compress_block, block): block 
                             for block in self.blocks}
            
            # Coleta resultados conforme completam
            completed = 0
            for future in as_completed(future_to_block):
                block = future.result()
                completed += 1
                if completed % 10 == 0 or completed == len(self.blocks):
                    print(f"Progresso: {completed}/{len(self.blocks)} blocos")
        
        # Calcula offsets dos blocos
        current_offset = 0
        for block in self.blocks:
            block.offset = current_offset
            current_offset += block.compressed_size
        
        self.total_compressed_size = sum(block.compressed_size for block in self.blocks)
        
        # Escreve arquivo TZP
        self._write_tzp_file(output_path, file_checksum_int)
        
        # Estatísticas
        compression_time = time.time() - start_time
        compression_ratio = self.total_compressed_size / self.total_original_size if self.total_original_size > 0 else 1.0
        speed_mbps = (self.total_original_size / (1024 * 1024)) / compression_time if compression_time > 0 else 0
        
        stats = {
            'original_size': self.total_original_size,
            'compressed_size': self.total_compressed_size,
            'compression_ratio': compression_ratio,
            'compression_time': compression_time,
            'speed_mbps': speed_mbps,
            'num_blocks': len(self.blocks)
        }
        
        print(f"\n=== Estatísticas de Compressão ===")
        print(f"Tamanho original: {stats['original_size']:,} bytes")
        print(f"Tamanho comprimido: {stats['compressed_size']:,} bytes")
        print(f"Taxa de compressão: {stats['compression_ratio']:.3f} ({100 * (1 - stats['compression_ratio']):.1f}% de redução)")
        print(f"Tempo de compressão: {stats['compression_time']:.2f} segundos")
        print(f"Velocidade: {stats['speed_mbps']:.1f} MB/s")
        print(f"Número de blocos: {stats['num_blocks']}")
        
        return stats
    
    def _write_tzp_file(self, output_path: str, file_checksum: int) -> None:
        """Escreve o arquivo TZP completo"""
        try:
            with open(output_path, 'wb') as f:
                # Escreve cabeçalho
                self._write_header(f, file_checksum)
                
                # Escreve tabela de blocos
                self._write_block_table(f)
                
                # Escreve dados comprimidos
                self._write_compressed_data(f)
                
        except IOError as e:
            raise Exception(f"Erro ao escrever arquivo TZP: {e}")
    
    def _write_header(self, f, file_checksum: int) -> None:
        """Escreve o cabeçalho TZP"""
        # Magic Number (4 bytes)
        f.write(struct.pack('<I', TZP_MAGIC))
        
        # Versão (2 bytes)
        f.write(struct.pack('<H', TZP_VERSION))
        
        # Flags globais (2 bytes)
        global_flags = FLAG_FULL_CHECKSUM
        f.write(struct.pack('<H', global_flags))
        
        # Tamanho original (8 bytes)
        f.write(struct.pack('<Q', self.total_original_size))
        
        # Número de blocos (4 bytes)
        f.write(struct.pack('<I', len(self.blocks)))
        
        # Tamanho do bloco (4 bytes)
        f.write(struct.pack('<I', self.block_size))
        
        # Checksum do arquivo (8 bytes)
        f.write(struct.pack('<Q', file_checksum))
        
        # Reservado (20 bytes)
        f.write(b'\x00' * 20)
    
    def _write_block_table(self, f) -> None:
        """Escreve a tabela de blocos"""
        for block in self.blocks:
            # Offset do bloco (8 bytes)
            f.write(struct.pack('<Q', block.offset))
            
            # Tamanho comprimido (4 bytes)
            f.write(struct.pack('<I', block.compressed_size))
            
            # Tamanho original (4 bytes)
            f.write(struct.pack('<I', block.original_size))
            
            # Algoritmo (1 byte)
            f.write(struct.pack('<B', block.algorithm))
            
            # Nível de compressão (1 byte)
            f.write(struct.pack('<B', block.compression_level))
            
            # Flags do bloco (2 bytes)
            f.write(struct.pack('<H', block.flags))
            
            # Checksum do bloco (4 bytes)
            f.write(struct.pack('<I', block.checksum))
    
    def _write_compressed_data(self, f) -> None:
        """Escreve os dados comprimidos"""
        for block in self.blocks:
            f.write(block.compressed_data)

def main():
    parser = argparse.ArgumentParser(description='TZP Encoder - Compressor Turbo Zip')
    parser.add_argument('input', help='Arquivo de entrada')
    parser.add_argument('output', help='Arquivo de saída (.tzp)')
    parser.add_argument('--block-size', type=int, default=DEFAULT_BLOCK_SIZE,
                       help=f'Tamanho do bloco em bytes (padrão: {DEFAULT_BLOCK_SIZE})')
    parser.add_argument('--threads', type=int, default=None,
                       help='Número de threads (padrão: auto)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Saída detalhada')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"Erro: Arquivo de entrada '{args.input}' não encontrado")
        sys.exit(1)
    
    if not args.output.endswith('.tzp'):
        print("Aviso: Arquivo de saída não tem extensão .tzp")
    
    try:
        encoder = TZPEncoder(block_size=args.block_size, num_threads=args.threads)
        stats = encoder.compress_file(args.input, args.output)
        
        print(f"\n✅ Compressão concluída com sucesso!")
        print(f"Arquivo TZP criado: {args.output}")
        
    except Exception as e:
        print(f"❌ Erro durante a compressão: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

