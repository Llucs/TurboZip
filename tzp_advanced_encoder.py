#!/usr/bin/env python3
"""
TZP Advanced Encoder - Turbo Zip Compressor (Versão Avançada)
Implementação avançada com detecção de conteúdo, pipeline híbrida e perfis adaptativos

Autor: Llucs
Versão: 2.0
"""

import os
import sys
import struct
import time
import hashlib
import threading
import mimetypes
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple, Optional, Dict, Any, Union
import argparse
import json

try:
    import lz4.block
    import lz4.frame
    import zstandard as zstd
except ImportError as e:
    print(f"Erro: Bibliotecas de compressão não encontradas: {e}")
    print("Instale com: pip install lz4 zstandard")
    sys.exit(1)

# Constantes do formato TZP v2.0
TZP_MAGIC = 0x545A5001  # "TZP\1" (versão 2.0)
TZP_VERSION = 0x0200     # Versão 2.0
DEFAULT_BLOCK_SIZE = 4 * 1024 * 1024  # 4MB por bloco (otimizado)

# Algoritmos de compressão
ALGO_UNCOMPRESSED = 0x00
ALGO_LZ4_FAST = 0x01
ALGO_LZ4_HC = 0x02
ALGO_ZSTD_FAST = 0x03
ALGO_ZSTD_BALANCED = 0x04
ALGO_ZSTD_HIGH = 0x05
ALGO_ZSTD_MAX = 0x06

# Tipos de conteúdo detectados
CONTENT_UNKNOWN = 0x00
CONTENT_TEXT = 0x01
CONTENT_BINARY = 0x02
CONTENT_ALREADY_COMPRESSED = 0x03
CONTENT_EXECUTABLE = 0x04
CONTENT_STRUCTURED = 0x05  # JSON, XML, etc.

# Flags
FLAG_CONTENT_DETECTED = 0x0001
FLAG_DICTIONARY_USED = 0x0002
FLAG_PREPROCESSED = 0x0004
FLAG_ENCRYPTED = 0x0008
FLAG_FULL_CHECKSUM = 0x0010

# Perfis de compressão
PROFILE_FAST = "fast"
PROFILE_BALANCED = "balanced" 
PROFILE_DEEP = "deep"
PROFILE_MAX = "max"

class ContentDetector:
    """Detector de tipo de conteúdo para otimização de compressão"""
    
    @staticmethod
    def detect_content_type(data: bytes, filename: str = "") -> Tuple[int, Dict[str, Any]]:
        """Detecta o tipo de conteúdo e retorna metadados"""
        metadata = {
            'entropy': ContentDetector._calculate_entropy(data),
            'mime_type': mimetypes.guess_type(filename)[0] if filename else None,
            'size': len(data)
        }
        
        # Verifica se já está comprimido (alta entropia)
        if metadata['entropy'] > 7.5:
            # Verifica assinaturas de formatos comprimidos
            if ContentDetector._is_compressed_format(data):
                return CONTENT_ALREADY_COMPRESSED, metadata
        
        # Detecta executáveis
        if ContentDetector._is_executable(data):
            return CONTENT_EXECUTABLE, metadata
        
        # Detecta texto estruturado
        if ContentDetector._is_structured_text(data):
            return CONTENT_STRUCTURED, metadata
        
        # Detecta texto simples
        if ContentDetector._is_text(data):
            return CONTENT_TEXT, metadata
        
        # Por padrão, considera binário
        return CONTENT_BINARY, metadata
    
    @staticmethod
    def _calculate_entropy(data: bytes) -> float:
        """Calcula entropia de Shannon dos dados"""
        if not data:
            return 0.0
        
        # Conta frequência de cada byte
        freq = [0] * 256
        for byte in data:
            freq[byte] += 1
        
        # Calcula entropia
        import math
        entropy = 0.0
        data_len = len(data)
        for count in freq:
            if count > 0:
                p = count / data_len
                entropy -= p * math.log2(p)
        
        return entropy
    
    @staticmethod
    def _is_compressed_format(data: bytes) -> bool:
        """Verifica se os dados já estão em formato comprimido"""
        if len(data) < 4:
            return False
        
        # Assinaturas de formatos comprimidos conhecidos
        signatures = [
            b'\x1f\x8b',        # GZIP
            b'PK\x03\x04',      # ZIP
            b'PK\x05\x06',      # ZIP (empty)
            b'PK\x07\x08',      # ZIP
            b'\x37\x7a\xbc\xaf\x27\x1c',  # 7Z
            b'\x28\xb5\x2f\xfd',  # ZSTD
            b'\x04\x22\x4d\x18',  # LZ4
            b'\xff\xd8\xff',    # JPEG
            b'\x89PNG',         # PNG
            b'GIF8',            # GIF
            b'\x00\x00\x00\x18ftypmp4',  # MP4 (parcial)
            b'\x1a\x45\xdf\xa3',  # WEBM/MKV
        ]
        
        for sig in signatures:
            if data.startswith(sig):
                return True
        
        return False
    
    @staticmethod
    def _is_executable(data: bytes) -> bool:
        """Verifica se é um executável"""
        if len(data) < 4:
            return False
        
        # Assinaturas de executáveis
        return (data.startswith(b'MZ') or      # PE/EXE
                data.startswith(b'\x7fELF') or # ELF
                data.startswith(b'\xfe\xed\xfa') or  # Mach-O
                data.startswith(b'\xcf\xfa\xed\xfe'))  # Mach-O
    
    @staticmethod
    def _is_structured_text(data: bytes) -> bool:
        """Verifica se é texto estruturado (JSON, XML, etc.)"""
        try:
            text = data.decode('utf-8', errors='ignore')[:1000]  # Primeiros 1000 chars
            text = text.strip()
            
            # JSON
            if (text.startswith('{') and '}' in text) or (text.startswith('[') and ']' in text):
                return True
            
            # XML
            if text.startswith('<?xml') or text.startswith('<'):
                return True
            
            # YAML
            if '---' in text or text.count(':') > text.count('\n') * 0.3:
                return True
                
        except:
            pass
        
        return False
    
    @staticmethod
    def _is_text(data: bytes) -> bool:
        """Verifica se é texto simples"""
        try:
            # Tenta decodificar como UTF-8
            text = data.decode('utf-8')
            
            # Verifica se tem caracteres de controle demais
            control_chars = sum(1 for c in text if ord(c) < 32 and c not in '\n\r\t')
            control_ratio = control_chars / len(text) if text else 0
            
            return control_ratio < 0.1  # Menos de 10% de caracteres de controle
        except:
            return False

class TZPAdvancedBlock:
    """Bloco avançado com detecção de conteúdo e pipeline híbrida"""
    
    def __init__(self, data: bytes, block_id: int, profile: str = PROFILE_BALANCED):
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
        self.profile = profile
        
        # Detecção de conteúdo
        self.content_type, self.content_metadata = ContentDetector.detect_content_type(data)
        if self.content_type != CONTENT_UNKNOWN:
            self.flags |= FLAG_CONTENT_DETECTED
    
    def calculate_checksum(self) -> int:
        """Calcula checksum CRC32 dos dados originais"""
        import zlib
        return zlib.crc32(self.original_data) & 0xffffffff
    
    def compress_with_algorithm(self, algorithm: int, level: int = 1) -> Tuple[bytes, int]:
        """Comprime com algoritmo específico"""
        try:
            if algorithm == ALGO_LZ4_FAST:
                compressed = lz4.block.compress(self.original_data, mode='fast')
            elif algorithm == ALGO_LZ4_HC:
                compressed = lz4.block.compress(self.original_data, mode='high_compression')
            elif algorithm == ALGO_ZSTD_FAST:
                cctx = zstd.ZstdCompressor(level=1)
                compressed = cctx.compress(self.original_data)
            elif algorithm == ALGO_ZSTD_BALANCED:
                cctx = zstd.ZstdCompressor(level=level)
                compressed = cctx.compress(self.original_data)
            elif algorithm == ALGO_ZSTD_HIGH:
                cctx = zstd.ZstdCompressor(level=level)
                compressed = cctx.compress(self.original_data)
            elif algorithm == ALGO_ZSTD_MAX:
                cctx = zstd.ZstdCompressor(level=22)  # Máximo
                compressed = cctx.compress(self.original_data)
            else:
                return self.original_data, self.original_size
            
            return compressed, len(compressed)
        except Exception as e:
            print(f"Erro na compressão {algorithm} do bloco {self.block_id}: {e}")
            return self.original_data, self.original_size
    
    def find_optimal_compression(self) -> None:
        """Encontra compressão ótima baseada no perfil e tipo de conteúdo"""
        # Se já está comprimido, não comprime
        if self.content_type == CONTENT_ALREADY_COMPRESSED:
            self.compressed_data = self.original_data
            self.compressed_size = self.original_size
            self.algorithm = ALGO_UNCOMPRESSED
            self.checksum = self.calculate_checksum()
            return
        
        # Define algoritmos a testar baseado no perfil
        algorithms_to_test = self._get_algorithms_for_profile()
        
        best_ratio = 1.0
        best_algorithm = ALGO_UNCOMPRESSED
        best_data = self.original_data
        best_level = 0
        
        # Testa cada algoritmo
        for algo, level in algorithms_to_test:
            compressed_data, compressed_size = self.compress_with_algorithm(algo, level)
            ratio = compressed_size / self.original_size if self.original_size > 0 else 1.0
            
            if ratio < best_ratio:
                best_ratio = ratio
                best_algorithm = algo
                best_data = compressed_data
                best_level = level
        
        # Se não há benefício significativo (< 3% de redução), não comprime
        if best_ratio > 0.97:
            self.compressed_data = self.original_data
            self.compressed_size = self.original_size
            self.algorithm = ALGO_UNCOMPRESSED
            self.compression_level = 0
        else:
            self.compressed_data = best_data
            self.compressed_size = len(best_data)
            self.algorithm = best_algorithm
            self.compression_level = best_level
        
        self.checksum = self.calculate_checksum()
    
    def _get_algorithms_for_profile(self) -> List[Tuple[int, int]]:
        """Retorna algoritmos a testar baseado no perfil e tipo de conteúdo"""
        if self.profile == PROFILE_FAST:
            return [(ALGO_LZ4_FAST, 1)]
        
        elif self.profile == PROFILE_BALANCED:
            if self.content_type == CONTENT_TEXT:
                return [(ALGO_LZ4_FAST, 1), (ALGO_ZSTD_BALANCED, 3)]
            elif self.content_type == CONTENT_STRUCTURED:
                return [(ALGO_ZSTD_BALANCED, 6)]
            else:
                return [(ALGO_LZ4_FAST, 1), (ALGO_ZSTD_BALANCED, 3)]
        
        elif self.profile == PROFILE_DEEP:
            if self.content_type == CONTENT_TEXT:
                return [(ALGO_LZ4_HC, 1), (ALGO_ZSTD_BALANCED, 6), (ALGO_ZSTD_HIGH, 15)]
            elif self.content_type == CONTENT_STRUCTURED:
                return [(ALGO_ZSTD_BALANCED, 6), (ALGO_ZSTD_HIGH, 19)]
            else:
                return [(ALGO_LZ4_HC, 1), (ALGO_ZSTD_BALANCED, 6), (ALGO_ZSTD_HIGH, 15)]
        
        elif self.profile == PROFILE_MAX:
            return [(ALGO_ZSTD_HIGH, 19), (ALGO_ZSTD_MAX, 22)]
        
        return [(ALGO_LZ4_FAST, 1)]

class TZPAdvancedEncoder:
    """Encoder avançado com pipeline híbrida e detecção de conteúdo"""
    
    def __init__(self, block_size: int = DEFAULT_BLOCK_SIZE, num_threads: int = None, 
                 profile: str = PROFILE_BALANCED):
        self.block_size = block_size
        self.num_threads = num_threads or min(8, os.cpu_count() or 1)
        self.profile = profile
        self.blocks: List[TZPAdvancedBlock] = []
        self.total_original_size = 0
        self.total_compressed_size = 0
        self.global_metadata = {}
        
    def compress_file(self, input_path: str, output_path: str) -> Dict[str, Any]:
        """Comprime um arquivo para o formato TZP v2.0"""
        start_time = time.time()
        
        print(f"🚀 Comprimindo com TZP v2.0 (perfil: {self.profile})")
        print(f"Entrada: {input_path} -> Saída: {output_path}")
        
        # Lê o arquivo de entrada
        try:
            with open(input_path, 'rb') as f:
                data = f.read()
        except IOError as e:
            raise Exception(f"Erro ao ler arquivo de entrada: {e}")
        
        self.total_original_size = len(data)
        print(f"📊 Tamanho original: {self.total_original_size:,} bytes")
        
        # Detecção global de conteúdo
        global_content_type, global_metadata = ContentDetector.detect_content_type(data, input_path)
        self.global_metadata = {
            'content_type': global_content_type,
            'entropy': global_metadata['entropy'],
            'mime_type': global_metadata.get('mime_type'),
            'profile': self.profile
        }
        
        print(f"🔍 Tipo detectado: {self._content_type_name(global_content_type)}")
        print(f"📈 Entropia: {global_metadata['entropy']:.2f}")
        
        # Calcula checksum do arquivo completo
        file_checksum = hashlib.sha256(data).digest()[:8]
        file_checksum_int = struct.unpack('<Q', file_checksum)[0]
        
        # Divide em blocos
        print(f"🔧 Dividindo em blocos de {self.block_size:,} bytes...")
        self.blocks = self._split_into_blocks(data)
        print(f"📦 Total de blocos: {len(self.blocks)}")
        
        # Comprime blocos em paralelo
        print(f"⚡ Comprimindo blocos usando {self.num_threads} threads...")
        self._compress_blocks_parallel()
        
        # Calcula offsets dos blocos
        current_offset = 0
        for block in self.blocks:
            block.offset = current_offset
            current_offset += block.compressed_size
        
        self.total_compressed_size = sum(block.compressed_size for block in self.blocks)
        
        # Escreve arquivo TZP
        self._write_tzp_file(output_path, file_checksum_int)
        
        # Estatísticas detalhadas
        stats = self._calculate_stats(start_time)
        self._print_detailed_stats(stats)
        
        return stats
    
    def _content_type_name(self, content_type: int) -> str:
        """Converte tipo de conteúdo para nome legível"""
        names = {
            CONTENT_UNKNOWN: "Desconhecido",
            CONTENT_TEXT: "Texto",
            CONTENT_BINARY: "Binário", 
            CONTENT_ALREADY_COMPRESSED: "Já comprimido",
            CONTENT_EXECUTABLE: "Executável",
            CONTENT_STRUCTURED: "Estruturado (JSON/XML)"
        }
        return names.get(content_type, f"Tipo {content_type}")
    
    def _split_into_blocks(self, data: bytes) -> List[TZPAdvancedBlock]:
        """Divide os dados em blocos avançados"""
        blocks = []
        block_id = 0
        
        for i in range(0, len(data), self.block_size):
            block_data = data[i:i + self.block_size]
            block = TZPAdvancedBlock(block_data, block_id, self.profile)
            blocks.append(block)
            block_id += 1
            
        return blocks
    
    def _compress_blocks_parallel(self) -> None:
        """Comprime blocos em paralelo"""
        with ThreadPoolExecutor(max_workers=self.num_threads) as executor:
            # Submete todos os blocos para compressão
            future_to_block = {executor.submit(self._compress_block, block): block 
                             for block in self.blocks}
            
            # Coleta resultados conforme completam
            completed = 0
            for future in as_completed(future_to_block):
                block = future.result()
                completed += 1
                if completed % 10 == 0 or completed == len(self.blocks):
                    print(f"📈 Progresso: {completed}/{len(self.blocks)} blocos")
    
    def _compress_block(self, block: TZPAdvancedBlock) -> TZPAdvancedBlock:
        """Comprime um bloco individual"""
        block.find_optimal_compression()
        return block
    
    def _calculate_stats(self, start_time: float) -> Dict[str, Any]:
        """Calcula estatísticas detalhadas"""
        compression_time = time.time() - start_time
        compression_ratio = self.total_compressed_size / self.total_original_size if self.total_original_size > 0 else 1.0
        speed_mbps = (self.total_original_size / (1024 * 1024)) / compression_time if compression_time > 0 else 0
        
        # Estatísticas por algoritmo
        algo_stats = {}
        for block in self.blocks:
            algo_name = self._algorithm_name(block.algorithm)
            if algo_name not in algo_stats:
                algo_stats[algo_name] = {'count': 0, 'original_size': 0, 'compressed_size': 0}
            
            algo_stats[algo_name]['count'] += 1
            algo_stats[algo_name]['original_size'] += block.original_size
            algo_stats[algo_name]['compressed_size'] += block.compressed_size
        
        return {
            'original_size': self.total_original_size,
            'compressed_size': self.total_compressed_size,
            'compression_ratio': compression_ratio,
            'compression_time': compression_time,
            'speed_mbps': speed_mbps,
            'num_blocks': len(self.blocks),
            'algorithm_stats': algo_stats,
            'global_metadata': self.global_metadata
        }
    
    def _algorithm_name(self, algorithm: int) -> str:
        """Converte código do algoritmo para nome"""
        names = {
            ALGO_UNCOMPRESSED: "Não comprimido",
            ALGO_LZ4_FAST: "LZ4 Fast",
            ALGO_LZ4_HC: "LZ4 HC",
            ALGO_ZSTD_FAST: "Zstd Fast",
            ALGO_ZSTD_BALANCED: "Zstd Balanced",
            ALGO_ZSTD_HIGH: "Zstd High",
            ALGO_ZSTD_MAX: "Zstd Max"
        }
        return names.get(algorithm, f"Algoritmo {algorithm}")
    
    def _print_detailed_stats(self, stats: Dict[str, Any]) -> None:
        """Imprime estatísticas detalhadas"""
        print(f"\n🎯 === Estatísticas TZP v2.0 ===")
        print(f"📊 Tamanho original: {stats['original_size']:,} bytes")
        print(f"📦 Tamanho comprimido: {stats['compressed_size']:,} bytes")
        print(f"🎯 Taxa de compressão: {stats['compression_ratio']:.3f} ({100 * (1 - stats['compression_ratio']):.1f}% de redução)")
        print(f"⏱️  Tempo de compressão: {stats['compression_time']:.2f} segundos")
        print(f"🚀 Velocidade: {stats['speed_mbps']:.1f} MB/s")
        print(f"📦 Número de blocos: {stats['num_blocks']}")
        
        print(f"\n🔧 === Algoritmos Utilizados ===")
        for algo, data in stats['algorithm_stats'].items():
            ratio = data['compressed_size'] / data['original_size'] if data['original_size'] > 0 else 1.0
            print(f"  {algo}: {data['count']} blocos, taxa {ratio:.3f}")
    
    def _write_tzp_file(self, output_path: str, file_checksum: int) -> None:
        """Escreve o arquivo TZP v2.0 completo"""
        try:
            with open(output_path, 'wb') as f:
                # Escreve cabeçalho
                self._write_header(f, file_checksum)
                
                # Escreve metadados globais
                self._write_global_metadata(f)
                
                # Escreve tabela de blocos
                self._write_block_table(f)
                
                # Escreve dados comprimidos
                self._write_compressed_data(f)
                
        except IOError as e:
            raise Exception(f"Erro ao escrever arquivo TZP: {e}")
    
    def _write_header(self, f, file_checksum: int) -> None:
        """Escreve o cabeçalho TZP v2.0"""
        # Magic Number (4 bytes)
        f.write(struct.pack('<I', TZP_MAGIC))
        
        # Versão (2 bytes)
        f.write(struct.pack('<H', TZP_VERSION))
        
        # Flags globais (2 bytes)
        global_flags = FLAG_FULL_CHECKSUM | FLAG_CONTENT_DETECTED
        f.write(struct.pack('<H', global_flags))
        
        # Tamanho original (8 bytes)
        f.write(struct.pack('<Q', self.total_original_size))
        
        # Número de blocos (4 bytes)
        f.write(struct.pack('<I', len(self.blocks)))
        
        # Tamanho do bloco (4 bytes)
        f.write(struct.pack('<I', self.block_size))
        
        # Checksum do arquivo (8 bytes)
        f.write(struct.pack('<Q', file_checksum))
        
        # Tamanho dos metadados globais (4 bytes) - placeholder
        metadata_size_pos = f.tell()
        f.write(struct.pack('<I', 0))
        
        # Reservado (16 bytes)
        f.write(b'\x00' * 16)
    
    def _write_global_metadata(self, f) -> None:
        """Escreve metadados globais em JSON"""
        metadata_json = json.dumps(self.global_metadata, separators=(',', ':')).encode('utf-8')
        
        # Volta para escrever o tamanho dos metadados
        current_pos = f.tell()
        f.seek(current_pos - 20)  # Volta para o campo de tamanho
        f.write(struct.pack('<I', len(metadata_json)))
        f.seek(current_pos)
        
        # Escreve os metadados
        f.write(metadata_json)
    
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
            
            # Tipo de conteúdo (1 byte)
            f.write(struct.pack('<B', block.content_type))
            
            # Reservado (1 byte)
            f.write(struct.pack('<B', 0))
    
    def _write_compressed_data(self, f) -> None:
        """Escreve os dados comprimidos"""
        for block in self.blocks:
            f.write(block.compressed_data)

def main():
    parser = argparse.ArgumentParser(description='TZP Advanced Encoder - Compressor Turbo Zip v2.0')
    parser.add_argument('input', help='Arquivo de entrada')
    parser.add_argument('output', help='Arquivo de saída (.tzp)')
    parser.add_argument('--profile', choices=[PROFILE_FAST, PROFILE_BALANCED, PROFILE_DEEP, PROFILE_MAX],
                       default=PROFILE_BALANCED, help='Perfil de compressão')
    parser.add_argument('--block-size', type=int, default=DEFAULT_BLOCK_SIZE,
                       help=f'Tamanho do bloco em bytes (padrão: {DEFAULT_BLOCK_SIZE})')
    parser.add_argument('--threads', type=int, default=None,
                       help='Número de threads (padrão: auto)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Saída detalhada')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"❌ Erro: Arquivo de entrada '{args.input}' não encontrado")
        sys.exit(1)
    
    if not args.output.endswith('.tzp'):
        print("⚠️  Aviso: Arquivo de saída não tem extensão .tzp")
    
    try:
        encoder = TZPAdvancedEncoder(
            block_size=args.block_size, 
            num_threads=args.threads,
            profile=args.profile
        )
        stats = encoder.compress_file(args.input, args.output)
        
        print(f"\n✅ Compressão TZP v2.0 concluída com sucesso!")
        print(f"📁 Arquivo TZP criado: {args.output}")
        
    except Exception as e:
        print(f"❌ Erro durante a compressão: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

