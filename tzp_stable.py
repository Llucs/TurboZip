#!/usr/bin/env python3
"""
TZP Stable - Turbo Zip Compressor (Versão Estável)
Implementação estável e otimizada com técnicas avançadas de compressão

Autor: Llucs
Versão: 3.1 Stable
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
import math
from collections import Counter

try:
    import lz4.block
    import lz4.frame
    import zstandard as zstd
except ImportError as e:
    print(f"Erro: Bibliotecas de compressão não encontradas: {e}")
    print("Instale com: pip install lz4 zstandard")
    sys.exit(1)

# Constantes do formato TZP Stable v3.1
TZP_MAGIC = 0x545A5003  # "TZP\3" (versão 3.1 Stable)
TZP_VERSION = 0x0301     # Versão 3.1
DEFAULT_BLOCK_SIZE = 4 * 1024 * 1024  # 4MB por bloco

# Algoritmos de compressão
ALGO_UNCOMPRESSED = 0x00
ALGO_LZ4_FAST = 0x01
ALGO_LZ4_HC = 0x02
ALGO_ZSTD_FAST = 0x03
ALGO_ZSTD_BALANCED = 0x04
ALGO_ZSTD_HIGH = 0x05
ALGO_ZSTD_MAX = 0x06
ALGO_HYBRID = 0x07
ALGO_ADAPTIVE = 0x08

# Tipos de conteúdo
CONTENT_UNKNOWN = 0x00
CONTENT_TEXT = 0x01
CONTENT_STRUCTURED = 0x02
CONTENT_BINARY = 0x03
CONTENT_COMPRESSED = 0x04
CONTENT_REPETITIVE = 0x05

# Perfis
PROFILE_LIGHTNING = "lightning"
PROFILE_FAST = "fast"
PROFILE_BALANCED = "balanced"
PROFILE_HIGH = "high"
PROFILE_MAX = "max"

class StableContentAnalyzer:
    """Analisador de conteúdo estável e eficiente"""
    
    @staticmethod
    def analyze(data: bytes, filename: str = "") -> Dict[str, Any]:
        """Análise rápida e estável do conteúdo"""
        if not data:
            return {
                'entropy': 0.0,
                'content_type': CONTENT_UNKNOWN,
                'compression_potential': 0.0,
                'recommended_algorithm': ALGO_UNCOMPRESSED
            }
        
        # Calcula entropia de forma segura
        entropy = StableContentAnalyzer._safe_entropy(data)
        
        # Detecta tipo de conteúdo
        content_type = StableContentAnalyzer._detect_type(data, filename, entropy)
        
        # Estima potencial de compressão
        compression_potential = StableContentAnalyzer._estimate_potential(entropy, content_type)
        
        # Recomenda algoritmo
        recommended_algorithm = StableContentAnalyzer._recommend_algorithm(
            content_type, compression_potential, len(data)
        )
        
        return {
            'entropy': entropy,
            'content_type': content_type,
            'compression_potential': compression_potential,
            'recommended_algorithm': recommended_algorithm,
            'size': len(data)
        }
    
    @staticmethod
    def _safe_entropy(data: bytes) -> float:
        """Calcula entropia de forma segura"""
        if len(data) == 0:
            return 0.0
        
        # Amostra para arquivos grandes
        sample_size = min(len(data), 64 * 1024)
        sample = data[:sample_size]
        
        # Conta bytes
        counts = [0] * 256
        for byte in sample:
            counts[byte] += 1
        
        # Calcula entropia
        entropy = 0.0
        sample_len = len(sample)
        
        for count in counts:
            if count > 0:
                p = count / sample_len
                entropy -= p * math.log2(p)
        
        return entropy
    
    @staticmethod
    def _detect_type(data: bytes, filename: str, entropy: float) -> int:
        """Detecta tipo de conteúdo de forma segura"""
        # Verifica se já está comprimido (alta entropia)
        if entropy > 7.5:
            return CONTENT_COMPRESSED
        
        # Verifica se é muito repetitivo (baixa entropia)
        if entropy < 2.0:
            return CONTENT_REPETITIVE
        
        # Verifica por extensão de arquivo
        if filename:
            ext = os.path.splitext(filename.lower())[1]
            
            # Arquivos de texto
            text_exts = {".txt", ".log", ".csv", ".md", ".py", ".js", ".html", ".css", ".sql"}
            if ext in text_exts:
                return CONTENT_TEXT
            
            # Arquivos estruturados
            struct_exts = {".json", ".xml", ".yaml", ".yml", ".config", ".ini"}
            if ext in struct_exts:
                return CONTENT_STRUCTURED
            
            # Arquivos já comprimidos
            comp_exts = {".zip", ".gz", ".7z", ".rar", ".jpg", ".png", ".mp4", ".mp3"}
            if ext in comp_exts:
                return CONTENT_COMPRESSED
        
        # Verifica conteúdo dos primeiros bytes
        if len(data) >= 4:
            # Assinaturas de arquivos comprimidos
            if (data.startswith(b"\x1f\x8b") or  # GZIP
                data.startswith(b"PK") or        # ZIP
                data.startswith(b"\xff\xd8") or  # JPEG
                data.startswith(b"\x89PNG")):    # PNG
                return CONTENT_COMPRESSED
        
        # Tenta detectar texto
        try:
            sample = data[:1024].decode("utf-8", errors="strict")
            # Se decodificou sem erro, provavelmente é texto
            
            # Verifica se é estruturado
            if (sample.strip().startswith(("{", "[", "<")) or
                ":" in sample and sample.count(":") > sample.count("\n") * 0.3):
                return CONTENT_STRUCTURED
            
            return CONTENT_TEXT
        except:
            pass
        
        return CONTENT_BINARY
    
    @staticmethod
    def _estimate_potential(entropy: float, content_type: int) -> float:
        """Estima potencial de compressão"""
        # Baseado na entropia
        entropy_factor = max(0, (8.0 - entropy) / 8.0)
        
        # Ajuste baseado no tipo
        type_multiplier = {
            CONTENT_REPETITIVE: 1.0,
            CONTENT_TEXT: 0.8,
            CONTENT_STRUCTURED: 0.9,
            CONTENT_BINARY: 0.6,
            CONTENT_COMPRESSED: 0.1,
            CONTENT_UNKNOWN: 0.5
        }.get(content_type, 0.5)
        
        return entropy_factor * type_multiplier
    
    @staticmethod
    def _recommend_algorithm(content_type: int, potential: float, size: int) -> int:
        """Recomenda algoritmo baseado na análise"""
        # Arquivos já comprimidos - não comprimir
        if content_type == CONTENT_COMPRESSED:
            return ALGO_UNCOMPRESSED
        
        # Arquivos pequenos - LZ4 rápido
        if size < 64 * 1024:
            return ALGO_LZ4_FAST
        
        # Alto potencial - compressão máxima
        if potential > 0.8:
            return ALGO_ZSTD_MAX
        
        # Médio potencial - compressão balanceada
        if potential > 0.5:
            return ALGO_ZSTD_BALANCED
        
        # Baixo potencial - compressão rápida
        if potential > 0.2:
            return ALGO_LZ4_HC
        
        # Muito baixo potencial - não comprimir
        return ALGO_UNCOMPRESSED

class StableCompressor:
    """Compressor estável com algoritmos otimizados"""
    
    def __init__(self):
        self.zstd_compressors = {}
    
    def compress_smart(self, data: bytes, analysis: Dict[str, Any], profile: str) -> Tuple[bytes, int]:
        """Compressão inteligente baseada no perfil"""
        recommended_algo = analysis["recommended_algorithm"]
        
        # Ajusta algoritmo baseado no perfil
        if profile == PROFILE_LIGHTNING:
            algorithm = ALGO_LZ4_FAST
        elif profile == PROFILE_FAST:
            algorithm = min(recommended_algo, ALGO_LZ4_HC)
        elif profile == PROFILE_BALANCED:
            algorithm = recommended_algo
        elif profile == PROFILE_HIGH:
            if recommended_algo <= ALGO_ZSTD_BALANCED:
                algorithm = ALGO_ZSTD_HIGH
            else:
                algorithm = recommended_algo
        elif profile == PROFILE_MAX:
            if recommended_algo != ALGO_UNCOMPRESSED:
                algorithm = ALGO_ZSTD_MAX
            else:
                algorithm = ALGO_UNCOMPRESSED
        else:
            algorithm = recommended_algo
        
        # Executa compressão
        return self._compress_with_algorithm(data, algorithm)
    
    def _compress_with_algorithm(self, data: bytes, algorithm: int) -> Tuple[bytes, int]:
        """Comprime com algoritmo específico"""
        try:
            if algorithm == ALGO_UNCOMPRESSED:
                return data, ALGO_UNCOMPRESSED
            
            elif algorithm == ALGO_LZ4_FAST:
                compressed = lz4.frame.compress(data, compression_level=0) # Level 0 for fast
                return compressed, ALGO_LZ4_FAST
            
            elif algorithm == ALGO_LZ4_HC:
                compressed = lz4.frame.compress(data, compression_level=9) # High compression for HC
                return compressed, ALGO_LZ4_HC
            
            elif algorithm == ALGO_ZSTD_FAST:
                compressed = self._get_zstd_compressor(1).compress(data)
                return compressed, ALGO_ZSTD_FAST
            
            elif algorithm == ALGO_ZSTD_BALANCED:
                compressed = self._get_zstd_compressor(6).compress(data)
                return compressed, ALGO_ZSTD_BALANCED
            
            elif algorithm == ALGO_ZSTD_HIGH:
                compressed = self._get_zstd_compressor(15).compress(data)
                return compressed, ALGO_ZSTD_HIGH
            
            elif algorithm == ALGO_ZSTD_MAX:
                compressed = self._get_zstd_compressor(22).compress(data)
                return compressed, ALGO_ZSTD_MAX
            
            elif algorithm == ALGO_HYBRID:
                # Híbrido: LZ4 HC + Zstd
                lz4_compressed = lz4.block.compress(data, mode="high_compression")
                if len(lz4_compressed) < len(data) * 0.9:
                    final_compressed = self._get_zstd_compressor(6).compress(lz4_compressed)
                    if len(final_compressed) < len(lz4_compressed) * 0.95:
                        return final_compressed, ALGO_HYBRID
                    return lz4_compressed, ALGO_LZ4_HC
                return data, ALGO_UNCOMPRESSED
            
            else:
                return data, ALGO_UNCOMPRESSED
                
        except Exception as e:
            print(f"Erro na compressão: {e}")
            return data, ALGO_UNCOMPRESSED
    
    def _get_zstd_compressor(self, level: int) -> zstd.ZstdCompressor:
        """Obtém compressor Zstd com cache"""
        if level not in self.zstd_compressors:
            self.zstd_compressors[level] = zstd.ZstdCompressor(level=level)
        return self.zstd_compressors[level]

class TZPStableBlock:
    """Bloco TZP estável"""
    
    def __init__(self, data: bytes, block_id: int, profile: str):
        self.block_id = block_id
        self.original_data = data
        self.original_size = len(data)
        self.compressed_data = None
        self.compressed_size = 0
        self.algorithm = ALGO_UNCOMPRESSED
        self.checksum = 0
        self.profile = profile
        
        # Análise do conteúdo
        self.analysis = StableContentAnalyzer.analyze(data)
    
    def compress(self, compressor: StableCompressor) -> None:
        """Comprime o bloco"""
        # Compressão inteligente
        compressed_data, algorithm = compressor.compress_smart(
            self.original_data, self.analysis, self.profile
        )
        
        # Verifica se vale a pena comprimir
        if len(compressed_data) >= len(self.original_data) * 0.98:
            # Não vale a pena, mantém original
            self.compressed_data = self.original_data
            self.compressed_size = self.original_size
            self.algorithm = ALGO_UNCOMPRESSED
        else:
            self.compressed_data = compressed_data
            self.compressed_size = len(compressed_data)
            self.algorithm = algorithm
        
        # Calcula checksum
        import zlib
        self.checksum = zlib.crc32(self.original_data) & 0xffffffff

class TZPStableEncoder:
    """Encoder TZP estável e otimizado"""
    
    def __init__(self, block_size: int = DEFAULT_BLOCK_SIZE, 
                 num_threads: int = None, profile: str = PROFILE_BALANCED):
        self.block_size = block_size
        self.num_threads = num_threads or min(8, os.cpu_count() or 1)
        self.profile = profile
        self.blocks: List[TZPStableBlock] = []
        self.compressor = StableCompressor()
        
    def compress_file(self, input_path: str, output_path: str) -> Dict[str, Any]:
        """Comprime arquivo completo"""
        start_time = time.time()
        
        print(f"🚀 TZP Stable v3.1 - Compressor Otimizado")
        print(f"👤 Desenvolvido por: Llucs")
        print(f"🎯 Perfil: {self.profile.upper()}")
        print(f"📁 {input_path} → {output_path}")
        
        # Lê arquivo
        try:
            with open(input_path, "rb") as f:
                data = f.read()
        except IOError as e:
            raise Exception(f"Erro ao ler arquivo: {e}")
        
        original_size = len(data)
        print(f"📊 Tamanho original: {original_size:,} bytes")
        
        # Análise global
        global_analysis = StableContentAnalyzer.analyze(data, input_path)
        self._print_analysis(global_analysis)
        
        # Divide em blocos
        print(f"🔧 Dividindo em blocos de {self.block_size:,} bytes...")
        self.blocks = self._create_blocks(data)
        print(f"📦 Total de blocos: {len(self.blocks)}")
        
        # Compressão paralela
        print(f"⚡ Comprimindo com {self.num_threads} threads...")
        self._compress_parallel()
        
        # Escreve arquivo
        self._write_file(output_path)
        
        # Estatísticas
        stats = self._calculate_stats(start_time, original_size)
        self._print_stats(stats)
        
        return stats
    
    def _print_analysis(self, analysis: Dict[str, Any]) -> None:
        """Imprime análise do conteúdo"""
        type_names = {
            CONTENT_TEXT: "Texto",
            CONTENT_STRUCTURED: "Estruturado",
            CONTENT_BINARY: "Binário",
            CONTENT_COMPRESSED: "Já comprimido",
            CONTENT_REPETITIVE: "Repetitivo"
        }
        
        type_name = type_names.get(analysis["content_type"], "Desconhecido")
        
        print(f"🔍 Tipo: {type_name}")
        print(f'📈 Entropia: {analysis["entropy"]:.2f}/8.0')
        print(f'🎯 Potencial: {analysis["compression_potential"]*100:.1f}%')
    
    def _create_blocks(self, data: bytes) -> List[TZPStableBlock]:
        """Cria blocos de dados"""
        blocks = []
        block_id = 0
        
        for i in range(0, len(data), self.block_size):
            block_data = data[i:i + self.block_size]
            block = TZPStableBlock(block_data, block_id, self.profile)
            blocks.append(block)
            block_id += 1
        
        return blocks
    
    def _compress_parallel(self) -> None:
        """Compressão paralela dos blocos"""
        with ThreadPoolExecutor(max_workers=self.num_threads) as executor:
            futures = [executor.submit(self._compress_block, block) for block in self.blocks]
            
            completed = 0
            for future in as_completed(futures):
                future.result()  # Aguarda conclusão
                completed += 1
                
                if completed % max(1, len(self.blocks) // 4) == 0 or completed == len(self.blocks):
                    progress = (completed / len(self.blocks)) * 100
                    print(f"📈 Progresso: {completed}/{len(self.blocks)} ({progress:.0f}%)")
    
    def _compress_block(self, block: TZPStableBlock) -> None:
        """Comprime um bloco"""
        block.compress(self.compressor)
    
    def _write_file(self, output_path: str) -> None:
        """Escreve arquivo TZP"""
        try:
            with open(output_path, "wb") as f:
                self._write_header(f)
                self._write_block_table(f)
                self._write_data(f)
        except IOError as e:
            raise Exception(f"Erro ao escrever arquivo: {e}")
    
    def _write_header(self, f) -> None:
        """Escreve cabeçalho"""
        total_original = sum(block.original_size for block in self.blocks)
        
        # Magic + Version
        f.write(struct.pack("<IH", TZP_MAGIC, TZP_VERSION))
        
        # Flags (2 bytes)
        f.write(struct.pack("<H", 0x0001))  # FLAG_OPTIMIZED
        
        # Tamanho original (8 bytes)
        f.write(struct.pack("<Q", total_original))
        
        # Número de blocos (4 bytes)
        f.write(struct.pack("<I", len(self.blocks)))
        
        # Tamanho do bloco (4 bytes)
        f.write(struct.pack("<I", self.block_size))
        
        # Checksum global (8 bytes)
        global_checksum = hashlib.sha256(str(total_original).encode()).digest()[:8]
        f.write(global_checksum)
        
        # Reservado (16 bytes)
        f.write(b"\x00" * 16)
    
    def _write_block_table(self, f) -> None:
        """Escreve tabela de blocos"""
        offset = 0
        
        for block in self.blocks:
            # Offset (8 bytes)
            f.write(struct.pack("<Q", offset))
            
            # Tamanhos (4 + 4 bytes)
            f.write(struct.pack("<II", block.compressed_size, block.original_size))
            
            # Algoritmo (1 byte)
            f.write(struct.pack("<B", block.algorithm))
            
            # Flags (1 byte)
            f.write(struct.pack("<B", 0))
            
            # Checksum (4 bytes)
            f.write(struct.pack("<I", block.checksum))
            
            # Reservado (2 bytes)
            f.write(struct.pack("<H", 0))
            
            offset += block.compressed_size
    
    def _write_data(self, f) -> None:
        """Escreve dados comprimidos"""
        for block in self.blocks:
            f.write(block.compressed_data)
    
    def _calculate_stats(self, start_time: float, original_size: int) -> Dict[str, Any]:
        """Calcula estatísticas"""
        compressed_size = sum(block.compressed_size for block in self.blocks)
        compression_time = time.time() - start_time
        
        return {
            'original_size': original_size,
            'compressed_size': compressed_size,
            'compression_ratio': compressed_size / original_size if original_size > 0 else 1.0,
            'compression_time': compression_time,
            'speed_mbps': (original_size / (1024*1024)) / compression_time if compression_time > 0 else 0,
            'num_blocks': len(self.blocks),
            'profile': self.profile
        }
    
    def _print_stats(self, stats: Dict[str, Any]) -> None:
        """Imprime estatísticas finais"""
        reduction = (1 - stats["compression_ratio"]) * 100
        
        print(f"\n🎯 === Resultados TZP Stable v3.1 ===")
        print(f'📊 Original: {stats["original_size"]:,} bytes')
        print(f'📦 Comprimido: {stats["compressed_size"]:,} bytes')
        print(f'🎯 Redução: {reduction:.2f}%')
        print(f'⏱️  Tempo: {stats["compression_time"]:.2f}s')
        print(f'🚀 Velocidade: {stats["speed_mbps"]:.1f} MB/s')

class TZPStableDecoder:
    """Decoder TZP estável e otimizado"""

    def __init__(self):
        self.zstd_decompressors = {}

    def decompress_file(self, input_path: str, output_path: str) -> Dict[str, Any]:
        """Descomprime arquivo completo"""
        start_time = time.time()

        print(f"🚀 TZP Stable v3.1 - Descompressor Otimizado")
        print(f"👤 Desenvolvido por: Llucs")
        print(f"📁 {input_path} → {output_path}")

        try:
            with open(input_path, "rb") as f:
                header = self._read_header(f)
                block_table = self._read_block_table(f, header)
                original_data = self._decompress_data(f, block_table, header)
        except IOError as e:
            raise Exception(f"Erro ao ler arquivo TZP: {e}")
        except Exception as e:
            raise Exception(f"Erro na descompressão: {e}")

        try:
            with open(output_path, "wb") as f:
                f.write(original_data)
        except IOError as e:
            raise Exception(f"Erro ao escrever arquivo de saída: {e}")

        stats = self._calculate_stats(start_time, len(original_data))
        self._print_stats(stats)

        return stats

    def _read_header(self, f) -> Dict[str, Any]:
        """Lê cabeçalho do arquivo TZP"""
        magic, version = struct.unpack("<IH", f.read(6))
        if magic != TZP_MAGIC or version != TZP_VERSION:
            raise Exception("Arquivo TZP inválido ou versão incompatível.")

        flags, original_size, num_blocks, block_size = struct.unpack("<HQLI", f.read(18))
        global_checksum = f.read(8)
        reserved = f.read(16)

        return {
            'magic': magic,
            'version': version,
            'flags': flags,
            'original_size': original_size,
            'num_blocks': num_blocks,
            'block_size': block_size,
            'global_checksum': global_checksum
        }

    def _read_block_table(self, f, header: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Lê tabela de blocos"""
        block_table = []
        for _ in range(header["num_blocks"]):
            offset, compressed_size, original_size, algorithm, flags, checksum, reserved = struct.unpack("<QIIBBIH", f.read(24))
            block_table.append({
                'offset': offset,
                'compressed_size': compressed_size,
                'original_size': original_size,
                'algorithm': algorithm,
                'flags': flags,
                'checksum': checksum,
                'reserved': reserved
            })
        return block_table

    def _decompress_data(self, f, block_table: List[Dict[str, Any]], header: Dict[str, Any]) -> bytes:
        """Descomprime todos os blocos"""
        decompressed_parts = [None] * len(block_table)
        
        with ThreadPoolExecutor(max_workers=os.cpu_count() or 1) as executor:
            futures = []
            # Store current file position to restore it later
            current_pos = f.tell()
            for i, block_info in enumerate(block_table):
                f.seek(self._get_data_offset(header) + block_info["offset"])
                compressed_data = f.read(block_info["compressed_size"])
                futures.append(executor.submit(self._decompress_block, compressed_data, block_info, i))
            
            # Restore file position
            f.seek(current_pos)

            for future in as_completed(futures):
                index, decompressed_block = future.result()
                decompressed_parts[index] = decompressed_block

        return b"".join(decompressed_parts)

    def _decompress_block(self, compressed_data: bytes, block_info: Dict[str, Any], index: int) -> Tuple[int, bytes]:
        """Descomprime um único bloco"""
        algorithm = block_info["algorithm"]
        original_size = block_info["original_size"]
        checksum = block_info["checksum"]

        decompressed_data = b""
        try:
            if algorithm == ALGO_UNCOMPRESSED:
                decompressed_data = compressed_data
            elif algorithm == ALGO_LZ4_FAST or algorithm == ALGO_LZ4_HC:
                decompressed_data = lz4.frame.decompress(compressed_data) # Use lz4.frame for decompression
                
            elif algorithm >= ALGO_ZSTD_FAST and algorithm <= ALGO_ZSTD_MAX:
                decompressed_data = self._get_zstd_decompressor().decompress(compressed_data)
            elif algorithm == ALGO_HYBRID:
                # Híbrido: Zstd -> LZ4 HC
                intermediate_data = self._get_zstd_decompressor().decompress(compressed_data)
                decompressed_data = lz4.block.decompress(intermediate_data, uncompressed_size=original_size)
            else:
                raise Exception(f"Algoritmo de descompressão desconhecido: {algorithm}")
        except Exception as e:
            raise Exception(f"Erro ao descomprimir bloco (algoritmo {algorithm}): {e}")

        # Verifica checksum
        import zlib
        if zlib.crc32(decompressed_data) & 0xffffffff != checksum:
            raise Exception(f"Checksum do bloco {index} inválido!")

        return index, decompressed_data

    def _get_zstd_decompressor(self) -> zstd.ZstdDecompressor:
        """Obtém descompressor Zstd com cache"""
        if not hasattr(self, "_zstd_decompressor"):
            self._zstd_decompressor = zstd.ZstdDecompressor()
        return self._zstd_decompressor

    def _get_data_offset(self, header: Dict[str, Any]) -> int:
        """Calcula offset do início dos dados comprimidos"""
        # Tamanho do cabeçalho fixo + tamanho da tabela de blocos
        return 48 + (header["num_blocks"] * 24)

    def _calculate_stats(self, start_time: float, original_size: int) -> Dict[str, Any]:
        """Calcula estatísticas"""
        decompression_time = time.time() - start_time
        
        return {
            'original_size': original_size,
            'decompression_time': decompression_time,
            'speed_mbps': (original_size / (1024*1024)) / decompression_time if decompression_time > 0 else 0,
        }
    
    def _print_stats(self, stats: Dict[str, Any]) -> None:
        """Imprime estatísticas finais"""
        print(f"\n🎯 === Resultados TZP Stable v3.1 ===")
        print(f'📊 Original: {stats["original_size"]:,} bytes')
        print(f'⏱️  Tempo de descompressão: {stats["decompression_time"]:.2f}s')
        print(f'🚀 Velocidade de descompressão: {stats["speed_mbps"]:.1f} MB/s')

def main():
    parser = argparse.ArgumentParser(
        description='TZP Stable v3.1 - Compressor/Descompressor Otimizado',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Comandos:
  compress   - Comprime um arquivo para o formato .tzp
  decompress - Descomprime um arquivo .tzp
  info       - Exibe metadados de um arquivo .tzp

Perfis de compressão disponíveis:
  lightning  - Máxima velocidade (LZ4 rápido)
  fast       - Velocidade alta (LZ4 HC)
  balanced   - Equilíbrio ideal (padrão)
  high       - Alta compressão (Zstd alto)
  max        - Máxima compressão (Zstd 22)

Desenvolvido por: Llucs
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Comando a executar')

    # Subcomando 'compress'
    compress_parser = subparsers.add_parser('compress', help='Comprime um arquivo')
    compress_parser.add_argument('input', help='Arquivo de entrada')
    compress_parser.add_argument('output', help='Arquivo de saída (.tzp)')
    compress_parser.add_argument('-p', '--profile', 
                                 choices=[PROFILE_LIGHTNING, PROFILE_FAST, PROFILE_BALANCED, 
                                          PROFILE_HIGH, PROFILE_MAX],
                                 default=PROFILE_BALANCED, help='Perfil de compressão')
    compress_parser.add_argument('--block-size', type=int, default=DEFAULT_BLOCK_SIZE,
                                 help='Tamanho do bloco em bytes')
    compress_parser.add_argument('-t', '--threads', type=int,
                                 help='Número de threads')

    # Subcomando 'decompress'
    decompress_parser = subparsers.add_parser('decompress', help='Descomprime um arquivo .tzp')
    decompress_parser.add_argument('input', help='Arquivo .tzp de entrada')
    decompress_parser.add_argument('output', help='Arquivo de saída')
    decompress_parser.add_argument('-t', '--threads', type=int,
                                   help='Número de threads para descompressão')

    # Subcomando 'info'
    info_parser = subparsers.add_parser('info', help='Exibe metadados de um arquivo .tzp')
    info_parser.add_argument('input', help='Arquivo .tzp de entrada')
    
    args = parser.parse_args()
    
    if args.command == 'compress':
        if not os.path.exists(args.input):
            print(f"❌ Erro: Arquivo '{args.input}' não encontrado")
            sys.exit(1)
        
        try:
            encoder = TZPStableEncoder(
                block_size=args.block_size,
                num_threads=args.threads,
                profile=args.profile
            )
            
            stats = encoder.compress_file(args.input, args.output)
            print(f"\n✅ Arquivo TZP criado: {args.output}")
            
        except Exception as e:
            print(f"❌ Erro na compressão: {e}")
            sys.exit(1)
    
    elif args.command == 'decompress':
        if not os.path.exists(args.input):
            print(f"❌ Erro: Arquivo '{args.input}' não encontrado")
            sys.exit(1)
        
        try:
            decoder = TZPStableDecoder()
            stats = decoder.decompress_file(args.input, args.output)
            print(f"\n✅ Arquivo descomprimido: {args.output}")
        except Exception as e:
            print(f"❌ Erro na descompressão: {e}")
            sys.exit(1)
    
    elif args.command == 'info':
        if not os.path.exists(args.input):
            print(f"❌ Erro: Arquivo '{args.input}' não encontrado")
            sys.exit(1)
        
        try:
            with open(args.input, "rb") as f:
                header = TZPStableDecoder()._read_header(f)
                block_table = TZPStableDecoder()._read_block_table(f, header)
            
            print(f"\n--- Metadados do Arquivo TZP: {args.input} ---")
            print(f"Magic Number: {hex(header['magic'])}")
            print(f"Versão: {header['version'] >> 8}.{header['version'] & 0xFF}")
            print(f"Tamanho Original: {header['original_size']:,} bytes")
            print(f"Número de Blocos: {header['num_blocks']}")
            print(f"Tamanho Base do Bloco: {header['block_size']:,} bytes")
            print(f"Checksum Global: {header['global_checksum'].hex()}")
            print(f"\n--- Tabela de Blocos ---")
            for i, block in enumerate(block_table):
                algo_name = {
                    ALGO_UNCOMPRESSED: "UNCOMPRESSED",
                    ALGO_LZ4_FAST: "LZ4_FAST",
                    ALGO_LZ4_HC: "LZ4_HC",
                    ALGO_ZSTD_FAST: "ZSTD_FAST",
                    ALGO_ZSTD_BALANCED: "ZSTD_BALANCED",
                    ALGO_ZSTD_HIGH: "ZSTD_HIGH",
                    ALGO_ZSTD_MAX: "ZSTD_MAX",
                    ALGO_HYBRID: "HYBRID",
                    ALGO_ADAPTIVE: "ADAPTIVE"
                }.get(block['algorithm'], "UNKNOWN")
                print(f"Bloco {i}: Offset={block['offset']:,}, Comprimido={block['compressed_size']:,} bytes, Original={block['original_size']:,} bytes, Algoritmo={algo_name}, Checksum={hex(block['checksum'])}")

        except Exception as e:
            print(f"❌ Erro ao ler metadados do arquivo TZP: {e}")
            sys.exit(1)

    else:
        parser.print_help()

if __name__ == "__main__":
    main()

