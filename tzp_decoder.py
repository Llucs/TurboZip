#!/usr/bin/env python3
"""
TZP Decoder - Turbo Zip Decompressor
Implementação do descompressor para o formato .tzp (Turbo Zip)

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
from typing import List, Tuple, Optional, Dict, Any, BinaryIO
import argparse

try:
    import lz4.block
    import zstandard as zstd
except ImportError as e:
    print(f"Erro: Bibliotecas de compressão não encontradas: {e}")
    print("Instale com: pip install lz4 zstandard")
    sys.exit(1)

# Constantes do formato TZP
TZP_MAGIC_V1 = 0x545A5000  # "TZP\0" (versão 1.0)
TZP_MAGIC_V2 = 0x545A5001  # "TZP\1" (versão 2.0)
TZP_VERSION_V1 = 0x0100     # Versão 1.0
TZP_VERSION_V2 = 0x0200     # Versão 2.0

# Algoritmos de compressão (compatibilidade v1 e v2)
ALGO_LZ4 = 0x00  # v1.0
ALGO_ZSTD = 0x01  # v1.0
ALGO_UNCOMPRESSED = 0xFF  # v1.0

# Novos algoritmos v2.0
ALGO_UNCOMPRESSED_V2 = 0x00
ALGO_LZ4_FAST = 0x01
ALGO_LZ4_HC = 0x02
ALGO_ZSTD_FAST = 0x03
ALGO_ZSTD_BALANCED = 0x04
ALGO_ZSTD_HIGH = 0x05
ALGO_ZSTD_MAX = 0x06

# Flags
FLAG_PREPROCESSED = 0x0001
FLAG_ENCRYPTED = 0x0001
FLAG_FULL_CHECKSUM = 0x0002

class TZPBlockInfo:
    """Informações sobre um bloco no arquivo TZP"""
    
    def __init__(self):
        self.offset = 0
        self.compressed_size = 0
        self.original_size = 0
        self.algorithm = ALGO_UNCOMPRESSED
        self.compression_level = 0
        self.flags = 0
        self.checksum = 0
        self.block_id = 0

class TZPHeader:
    """Cabeçalho do arquivo TZP"""
    
    def __init__(self):
        self.magic = 0
        self.version = 0
        self.global_flags = 0
        self.original_size = 0
        self.num_blocks = 0
        self.block_size = 0
        self.file_checksum = 0

class TZPDecoder:
    """Decoder principal para o formato TZP"""
    
    def __init__(self, num_threads: int = None):
        self.num_threads = num_threads or min(8, os.cpu_count() or 1)
        self.header = TZPHeader()
        self.blocks: List[TZPBlockInfo] = []
        self.file_handle: Optional[BinaryIO] = None
        
    def decompress_file(self, input_path: str, output_path: str) -> Dict[str, Any]:
        """Descomprime um arquivo TZP"""
        start_time = time.time()
        
        print(f"Descomprimindo: {input_path} -> {output_path}")
        
        try:
            with open(input_path, 'rb') as f:
                self.file_handle = f
                
                # Lê e valida o cabeçalho
                self._read_header()
                
                # Lê a tabela de blocos
                self._read_block_table()
                
                # Descomprime os dados
                decompressed_data = self._decompress_data()
                
                # Verifica integridade do arquivo completo
                if self.header.global_flags & FLAG_FULL_CHECKSUM:
                    self._verify_file_integrity(decompressed_data)
                
                # Escreve arquivo de saída
                with open(output_path, 'wb') as out_f:
                    out_f.write(decompressed_data)
                
        except IOError as e:
            raise Exception(f"Erro de E/S: {e}")
        except Exception as e:
            raise Exception(f"Erro durante descompressão: {e}")
        
        # Estatísticas
        decompression_time = time.time() - start_time
        compressed_size = os.path.getsize(input_path)
        compression_ratio = compressed_size / self.header.original_size if self.header.original_size > 0 else 1.0
        speed_mbps = (self.header.original_size / (1024 * 1024)) / decompression_time if decompression_time > 0 else 0
        
        stats = {
            'compressed_size': compressed_size,
            'original_size': self.header.original_size,
            'compression_ratio': compression_ratio,
            'decompression_time': decompression_time,
            'speed_mbps': speed_mbps,
            'num_blocks': self.header.num_blocks
        }
        
        print(f"\n=== Estatísticas de Descompressão ===")
        print(f"Tamanho comprimido: {stats['compressed_size']:,} bytes")
        print(f"Tamanho original: {stats['original_size']:,} bytes")
        print(f"Taxa de compressão: {stats['compression_ratio']:.3f} ({100 * (1 - stats['compression_ratio']):.1f}% de redução)")
        print(f"Tempo de descompressão: {stats['decompression_time']:.2f} segundos")
        print(f"Velocidade: {stats['speed_mbps']:.1f} MB/s")
        print(f"Número de blocos: {stats['num_blocks']}")
        
        return stats
    
    def _read_header(self) -> None:
        """Lê e valida o cabeçalho TZP"""
        # Lê cabeçalho básico primeiro
        basic_header = self.file_handle.read(32)
        if len(basic_header) != 32:
            raise Exception("Arquivo TZP inválido: cabeçalho incompleto")
        
        # Desempacota parte básica
        (magic, version, global_flags, original_size, num_blocks, 
         block_size, file_checksum) = struct.unpack('<IHHQIIQ', basic_header)
        
        # Valida magic number
        if magic not in [TZP_MAGIC_V1, TZP_MAGIC_V2]:
            raise Exception(f"Arquivo não é um TZP válido (magic: 0x{magic:08X})")
        
        # Valida versão
        if version not in [TZP_VERSION_V1, TZP_VERSION_V2]:
            raise Exception(f"Versão TZP não suportada: 0x{version:04X}")
        
        # Lê resto do cabeçalho baseado na versão
        if version == TZP_VERSION_V2:
            # TZP v2.0 tem campos adicionais
            extra_header = self.file_handle.read(24)  # 4 + 20 bytes
            if len(extra_header) != 24:
                raise Exception("Cabeçalho TZP v2.0 incompleto")
            metadata_size, = struct.unpack('<I', extra_header[:4])
            # Pula metadados globais
            if metadata_size > 0:
                self.file_handle.read(metadata_size)
        else:
            # TZP v1.0 tem cabeçalho de 52 bytes total
            extra_header = self.file_handle.read(20)  # Reservado
            if len(extra_header) != 20:
                raise Exception("Cabeçalho TZP v1.0 incompleto")
        
        # Preenche header
        self.header.magic = magic
        self.header.version = version
        self.header.global_flags = global_flags
        self.header.original_size = original_size
        self.header.num_blocks = num_blocks
        self.header.block_size = block_size
        self.header.file_checksum = file_checksum
        
        print(f"Arquivo TZP válido (versão {version >> 8}.{version & 0xFF})")
        print(f"Tamanho original: {original_size:,} bytes")
        print(f"Número de blocos: {num_blocks}")
        print(f"Tamanho do bloco: {block_size:,} bytes")
    
    def _read_block_table(self) -> None:
        """Lê a tabela de blocos"""
        self.blocks = []
        
        # Determina tamanho da entrada baseado na versão
        if self.header.version == TZP_VERSION_V2:
            entry_size = 24  # TZP v2.0 tem entradas maiores
        else:
            entry_size = 22  # TZP v1.0
        
        for i in range(self.header.num_blocks):
            block_data = self.file_handle.read(entry_size)
            
            if len(block_data) != entry_size:
                raise Exception(f"Tabela de blocos corrompida no bloco {i}")
            
            if self.header.version == TZP_VERSION_V2:
                # Desempacota entrada do bloco v2.0 (com tipo de conteúdo)
                (offset, compressed_size, original_size, algorithm, 
                 compression_level, flags, checksum, content_type, reserved) = struct.unpack('<QIIBBHIBB', block_data)
            else:
                # Desempacota entrada do bloco v1.0
                (offset, compressed_size, original_size, algorithm, 
                 compression_level, flags, checksum) = struct.unpack('<QIIBBHI', block_data)
                content_type = 0  # Não disponível em v1.0
            
            block_info = TZPBlockInfo()
            block_info.offset = offset
            block_info.compressed_size = compressed_size
            block_info.original_size = original_size
            block_info.algorithm = algorithm
            block_info.compression_level = compression_level
            block_info.flags = flags
            block_info.checksum = checksum
            block_info.block_id = i
            
            self.blocks.append(block_info)
        
        print(f"Tabela de blocos lida: {len(self.blocks)} blocos")
    
    def _decompress_data(self) -> bytes:
        """Descomprime todos os blocos de dados"""
        print(f"Descomprimindo blocos usando {self.num_threads} threads...")
        
        # Calcula offset base dos dados comprimidos
        if self.header.version == TZP_VERSION_V2:
            # Para TZP v2.0, precisa calcular dinamicamente baseado nos metadados
            # Volta ao início e recalcula
            current_pos = self.file_handle.tell()
            self.file_handle.seek(36)  # Posição do tamanho dos metadados
            metadata_size = struct.unpack('<I', self.file_handle.read(4))[0]
            self.file_handle.seek(current_pos)
            # Cabeçalho (56) + Metadados + Tabela de blocos (24 * num_blocks)
            data_offset = 56 + metadata_size + (self.header.num_blocks * 24)
        else:
            # TZP v1.0: Cabeçalho (52) + Tabela de blocos (22 * num_blocks)
            data_offset = 52 + (self.header.num_blocks * 22)
        
        # Descomprime blocos em paralelo
        with ThreadPoolExecutor(max_workers=self.num_threads) as executor:
            # Submete todos os blocos para descompressão
            future_to_block = {
                executor.submit(self._decompress_block, block, data_offset): block 
                for block in self.blocks
            }
            
            # Coleta resultados na ordem correta
            decompressed_blocks = [None] * len(self.blocks)
            completed = 0
            
            for future in as_completed(future_to_block):
                block_info = future_to_block[future]
                try:
                    decompressed_data = future.result()
                    decompressed_blocks[block_info.block_id] = decompressed_data
                    completed += 1
                    
                    if completed % 10 == 0 or completed == len(self.blocks):
                        print(f"Progresso: {completed}/{len(self.blocks)} blocos")
                        
                except Exception as e:
                    raise Exception(f"Erro ao descomprimir bloco {block_info.block_id}: {e}")
        
        # Concatena todos os blocos descomprimidos
        return b''.join(decompressed_blocks)
    
    def _decompress_block(self, block_info: TZPBlockInfo, data_offset: int) -> bytes:
        """Descomprime um bloco individual"""
        # Lê dados comprimidos do bloco
        self.file_handle.seek(data_offset + block_info.offset)
        compressed_data = self.file_handle.read(block_info.compressed_size)
        
        if len(compressed_data) != block_info.compressed_size:
            raise Exception(f"Dados insuficientes para o bloco {block_info.block_id}")
        
        # Descomprime baseado no algoritmo
        if (block_info.algorithm == ALGO_UNCOMPRESSED or 
            block_info.algorithm == ALGO_UNCOMPRESSED_V2):
            decompressed_data = compressed_data
        elif (block_info.algorithm == ALGO_LZ4 or 
              block_info.algorithm == ALGO_LZ4_FAST or 
              block_info.algorithm == ALGO_LZ4_HC):
            decompressed_data = self._decompress_lz4(compressed_data, block_info.original_size)
        elif (block_info.algorithm == ALGO_ZSTD or 
              block_info.algorithm == ALGO_ZSTD_FAST or
              block_info.algorithm == ALGO_ZSTD_BALANCED or
              block_info.algorithm == ALGO_ZSTD_HIGH or
              block_info.algorithm == ALGO_ZSTD_MAX):
            decompressed_data = self._decompress_zstd(compressed_data)
        else:
            raise Exception(f"Algoritmo de compressão desconhecido: {block_info.algorithm}")
        
        # Verifica tamanho
        if len(decompressed_data) != block_info.original_size:
            raise Exception(f"Tamanho incorreto após descompressão do bloco {block_info.block_id}")
        
        # Verifica checksum
        import zlib
        calculated_checksum = zlib.crc32(decompressed_data) & 0xffffffff
        if calculated_checksum != block_info.checksum:
            raise Exception(f"Checksum inválido no bloco {block_info.block_id}")
        
        return decompressed_data
    
    def _decompress_lz4(self, compressed_data: bytes, original_size: int) -> bytes:
        """Descomprime dados LZ4"""
        try:
            return lz4.block.decompress(compressed_data, uncompressed_size=original_size)
        except Exception as e:
            raise Exception(f"Erro na descompressão LZ4: {e}")
    
    def _decompress_zstd(self, compressed_data: bytes) -> bytes:
        """Descomprime dados Zstandard"""
        try:
            dctx = zstd.ZstdDecompressor()
            return dctx.decompress(compressed_data)
        except Exception as e:
            raise Exception(f"Erro na descompressão Zstd: {e}")
    
    def _verify_file_integrity(self, data: bytes) -> None:
        """Verifica a integridade do arquivo completo"""
        print("Verificando integridade do arquivo...")
        
        # Calcula checksum do arquivo descomprimido
        file_checksum = hashlib.sha256(data).digest()[:8]
        file_checksum_int = struct.unpack('<Q', file_checksum)[0]
        
        if file_checksum_int != self.header.file_checksum:
            raise Exception("Checksum do arquivo não confere - arquivo pode estar corrompido")
        
        print("✅ Integridade do arquivo verificada")
    
    def get_info(self, input_path: str) -> Dict[str, Any]:
        """Obtém informações sobre um arquivo TZP sem descomprimi-lo"""
        try:
            with open(input_path, 'rb') as f:
                self.file_handle = f
                
                # Lê cabeçalho e tabela de blocos
                self._read_header()
                self._read_block_table()
                
                # Analisa algoritmos usados
                algo_stats = {}
                for block in self.blocks:
                    algo_name = {
                        ALGO_LZ4: 'LZ4',
                        ALGO_ZSTD: 'Zstandard',
                        ALGO_UNCOMPRESSED: 'Não comprimido'
                    }.get(block.algorithm, f'Desconhecido ({block.algorithm})')
                    
                    if algo_name not in algo_stats:
                        algo_stats[algo_name] = {'count': 0, 'compressed_size': 0, 'original_size': 0}
                    
                    algo_stats[algo_name]['count'] += 1
                    algo_stats[algo_name]['compressed_size'] += block.compressed_size
                    algo_stats[algo_name]['original_size'] += block.original_size
                
                compressed_size = os.path.getsize(input_path)
                compression_ratio = compressed_size / self.header.original_size if self.header.original_size > 0 else 1.0
                
                return {
                    'file_path': input_path,
                    'version': f"{self.header.version >> 8}.{self.header.version & 0xFF}",
                    'original_size': self.header.original_size,
                    'compressed_size': compressed_size,
                    'compression_ratio': compression_ratio,
                    'num_blocks': self.header.num_blocks,
                    'block_size': self.header.block_size,
                    'algorithm_stats': algo_stats,
                    'has_checksum': bool(self.header.global_flags & FLAG_FULL_CHECKSUM)
                }
                
        except Exception as e:
            raise Exception(f"Erro ao ler informações do arquivo TZP: {e}")

def main():
    parser = argparse.ArgumentParser(description='TZP Decoder - Descompressor Turbo Zip')
    parser.add_argument('input', help='Arquivo TZP de entrada')
    parser.add_argument('output', nargs='?', help='Arquivo de saída (opcional para --info)')
    parser.add_argument('--threads', type=int, default=None,
                       help='Número de threads (padrão: auto)')
    parser.add_argument('--info', action='store_true',
                       help='Mostra informações sobre o arquivo TZP sem descomprimir')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Saída detalhada')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"Erro: Arquivo de entrada '{args.input}' não encontrado")
        sys.exit(1)
    
    if not args.input.endswith('.tzp'):
        print("Aviso: Arquivo de entrada não tem extensão .tzp")
    
    try:
        decoder = TZPDecoder(num_threads=args.threads)
        
        if args.info:
            # Mostra informações sobre o arquivo
            info = decoder.get_info(args.input)
            
            print(f"\n=== Informações do Arquivo TZP ===")
            print(f"Arquivo: {info['file_path']}")
            print(f"Versão TZP: {info['version']}")
            print(f"Tamanho original: {info['original_size']:,} bytes")
            print(f"Tamanho comprimido: {info['compressed_size']:,} bytes")
            print(f"Taxa de compressão: {info['compression_ratio']:.3f} ({100 * (1 - info['compression_ratio']):.1f}% de redução)")
            print(f"Número de blocos: {info['num_blocks']}")
            print(f"Tamanho do bloco: {info['block_size']:,} bytes")
            print(f"Checksum de arquivo: {'Sim' if info['has_checksum'] else 'Não'}")
            
            print(f"\n=== Algoritmos Utilizados ===")
            for algo, stats in info['algorithm_stats'].items():
                ratio = stats['compressed_size'] / stats['original_size'] if stats['original_size'] > 0 else 1.0
                print(f"{algo}: {stats['count']} blocos, {stats['compressed_size']:,} bytes comprimidos, "
                      f"taxa {ratio:.3f}")
        else:
            # Descomprime o arquivo
            if not args.output:
                print("Erro: Arquivo de saída é obrigatório para descompressão")
                sys.exit(1)
            
            stats = decoder.decompress_file(args.input, args.output)
            
            print(f"\n✅ Descompressão concluída com sucesso!")
            print(f"Arquivo extraído: {args.output}")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

