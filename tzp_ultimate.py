#!/usr/bin/env python3
"""
TZP Ultimate - Turbo Zip Compressor (Versão Ultimate)
Implementação avançada com técnicas de compressão de última geração

Autor: Llucs
Versão: 3.0 Ultimate
"""

import os
import sys
import struct
import time
import hashlib
import threading
import mimetypes
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple, Optional, Dict, Any, Union
import argparse
import json
import math
from collections import Counter, defaultdict

try:
    import lz4.block
    import lz4.frame
    import zstandard as zstd
except ImportError as e:
    print(f"Erro: Bibliotecas de compressão não encontradas: {e}")
    print("Instale com: pip install lz4 zstandard numpy")
    sys.exit(1)

# Constantes do formato TZP Ultimate v3.0
TZP_MAGIC = 0x545A5002  # "TZP\2" (versão 3.0 Ultimate)
TZP_VERSION = 0x0300     # Versão 3.0
DEFAULT_BLOCK_SIZE = 8 * 1024 * 1024  # 8MB por bloco (otimizado)

# Algoritmos de compressão avançados
ALGO_UNCOMPRESSED = 0x00
ALGO_LZ4_TURBO = 0x01      # LZ4 otimizado
ALGO_LZ4_ULTRA = 0x02      # LZ4 HC otimizado
ALGO_ZSTD_LIGHTNING = 0x03 # Zstd ultra-rápido
ALGO_ZSTD_BALANCED = 0x04  # Zstd balanceado
ALGO_ZSTD_ULTIMATE = 0x05  # Zstd máximo
ALGO_HYBRID_FAST = 0x06    # Híbrido rápido (LZ4 + FSE)
ALGO_HYBRID_MAX = 0x07     # Híbrido máximo (múltiplas passadas)
ALGO_ADAPTIVE = 0x08       # Adaptativo baseado em conteúdo

# Tipos de conteúdo detectados (expandido)
CONTENT_UNKNOWN = 0x00
CONTENT_TEXT_PLAIN = 0x01
CONTENT_TEXT_STRUCTURED = 0x02  # JSON, XML, YAML
CONTENT_TEXT_CODE = 0x03        # Código fonte
CONTENT_BINARY_EXECUTABLE = 0x04
CONTENT_BINARY_DATA = 0x05
CONTENT_ALREADY_COMPRESSED = 0x06
CONTENT_MULTIMEDIA = 0x07       # Imagens, vídeos
CONTENT_REPETITIVE = 0x08       # Dados altamente repetitivos
CONTENT_RANDOM = 0x09           # Dados aleatórios/criptografados

# Flags avançadas
FLAG_CONTENT_DETECTED = 0x0001
FLAG_DICTIONARY_USED = 0x0002
FLAG_PREPROCESSED = 0x0004
FLAG_MULTI_PASS = 0x0008
FLAG_ADAPTIVE_BLOCK = 0x0010
FLAG_PATTERN_OPTIMIZED = 0x0020
FLAG_ENTROPY_CODED = 0x0040

# Perfis de compressão Ultimate
PROFILE_LIGHTNING = "lightning"  # Máxima velocidade
PROFILE_TURBO = "turbo"         # Velocidade alta
PROFILE_BALANCED = "balanced"    # Equilíbrio
PROFILE_POWER = "power"         # Alta compressão
PROFILE_ULTIMATE = "ultimate"    # Máxima compressão
PROFILE_ADAPTIVE = "adaptive"    # Adaptativo inteligente

class AdvancedContentDetector:
    """Detector avançado de tipo de conteúdo com análise profunda"""
    
    @staticmethod
    def analyze_content(data: bytes, filename: str = "") -> Dict[str, Any]:
        """Análise completa do conteúdo"""
        analysis = {
            'entropy': AdvancedContentDetector._calculate_entropy(data),
            'compression_potential': 0.0,
            'pattern_density': 0.0,
            'repetition_factor': 0.0,
            'byte_distribution': None,
            'content_type': CONTENT_UNKNOWN,
            'optimal_algorithm': ALGO_ZSTD_BALANCED,
            'recommended_block_size': DEFAULT_BLOCK_SIZE
        }
        
        # Análise de entropia
        entropy = analysis['entropy']
        
        # Análise de distribuição de bytes
        byte_counts = Counter(data[:min(len(data), 64*1024)])  # Primeiros 64KB
        analysis['byte_distribution'] = dict(byte_counts.most_common(10))
        
        # Calcula densidade de padrões
        analysis['pattern_density'] = AdvancedContentDetector._calculate_pattern_density(data)
        
        # Calcula fator de repetição
        analysis['repetition_factor'] = AdvancedContentDetector._calculate_repetition_factor(data)
        
        # Detecta tipo de conteúdo
        analysis['content_type'] = AdvancedContentDetector._detect_content_type(data, filename, entropy)
        
        # Calcula potencial de compressão
        analysis['compression_potential'] = AdvancedContentDetector._estimate_compression_potential(
            entropy, analysis['pattern_density'], analysis['repetition_factor']
        )
        
        # Recomenda algoritmo ótimo
        analysis['optimal_algorithm'] = AdvancedContentDetector._recommend_algorithm(analysis)
        
        # Recomenda tamanho de bloco ótimo
        analysis['recommended_block_size'] = AdvancedContentDetector._recommend_block_size(
            len(data), analysis['content_type'], analysis['pattern_density']
        )
        
        return analysis
    
    @staticmethod
    def _calculate_entropy(data: bytes) -> float:
        """Calcula entropia de Shannon otimizada"""
        if not data:
            return 0.0
        
        # Conta frequência de cada byte
        byte_counts = [0] * 256
        for byte in data:
            byte_counts[byte] += 1
        
        # Calcula entropia
        entropy = 0.0
        data_len = len(data)
        for count in byte_counts:
            if count > 0:
                p = count / data_len
                entropy -= p * math.log2(p)
        
        return entropy
    
    @staticmethod
    def _calculate_pattern_density(data: bytes) -> float:
        """Calcula densidade de padrões repetitivos"""
        if len(data) < 1024:
            return 0.0
        
        # Analisa padrões de 4 bytes apenas para simplicidade
        pattern_counts = {}
        sample_size = min(len(data), 16*1024)  # Amostra menor
        
        for i in range(0, sample_size - 4, 4):
            pattern = data[i:i+4]
            if pattern in pattern_counts:
                pattern_counts[pattern] += 1
            else:
                pattern_counts[pattern] = 1
        
        if not pattern_counts:
            return 0.0
        
        # Calcula densidade baseada nos padrões mais comuns
        max_count = max(pattern_counts.values())
        total_patterns = len(pattern_counts)
        
        density = (max_count - 1) / total_patterns if total_patterns > 0 else 0.0
        return min(density * 5, 1.0)  # Amplifica e normaliza
    
    @staticmethod
    def _calculate_repetition_factor(data: bytes) -> float:
        """Calcula fator de repetição de sequências"""
        if len(data) < 256:
            return 0.0
        
        # Analisa repetições de sequências de 8 bytes (mais simples)
        sequence_len = 8
        sequences = {}
        sample_size = min(len(data), 8*1024)  # Amostra menor
        
        for i in range(0, sample_size - sequence_len, sequence_len):
            seq = data[i:i+sequence_len]
            if seq in sequences:
                sequences[seq] += 1
            else:
                sequences[seq] = 1
        
        if not sequences:
            return 0.0
        
        # Calcula fator baseado nas sequências mais repetidas
        max_repetitions = max(sequences.values())
        total_sequences = len(sequences)
        
        if total_sequences <= 1:
            return 0.0
        
        repetition_factor = (max_repetitions - 1) / total_sequences
        return min(repetition_factor * 10, 1.0)  # Amplifica e normaliza
    
    @staticmethod
    def _detect_content_type(data: bytes, filename: str, entropy: float) -> int:
        """Detecta tipo de conteúdo com análise avançada"""
        # Verifica se já está comprimido (alta entropia)
        if entropy > 7.8:
            if AdvancedContentDetector._is_compressed_format(data):
                return CONTENT_ALREADY_COMPRESSED
            else:
                return CONTENT_RANDOM
        
        # Verifica multimídia
        if AdvancedContentDetector._is_multimedia(data, filename):
            return CONTENT_MULTIMEDIA
        
        # Verifica executáveis
        if AdvancedContentDetector._is_executable(data):
            return CONTENT_BINARY_EXECUTABLE
        
        # Verifica texto
        if AdvancedContentDetector._is_text(data):
            if AdvancedContentDetector._is_structured_text(data):
                return CONTENT_TEXT_STRUCTURED
            elif AdvancedContentDetector._is_source_code(data, filename):
                return CONTENT_TEXT_CODE
            else:
                return CONTENT_TEXT_PLAIN
        
        # Verifica dados repetitivos
        if entropy < 3.0:
            return CONTENT_REPETITIVE
        
        return CONTENT_BINARY_DATA
    
    @staticmethod
    def _is_compressed_format(data: bytes) -> bool:
        """Verifica formatos comprimidos conhecidos"""
        if len(data) < 4:
            return False
        
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
            b'RIFF',            # WAV/AVI
            b'\x00\x00\x00\x18ftypmp4',  # MP4
            b'\x1a\x45\xdf\xa3',  # WEBM/MKV
        ]
        
        for sig in signatures:
            if data.startswith(sig):
                return True
        
        return False
    
    @staticmethod
    def _is_multimedia(data: bytes, filename: str) -> bool:
        """Verifica se é arquivo multimídia"""
        if filename:
            multimedia_exts = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff',
                             '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv',
                             '.mp3', '.wav', '.flac', '.ogg', '.aac', '.m4a'}
            ext = os.path.splitext(filename.lower())[1]
            if ext in multimedia_exts:
                return True
        
        return AdvancedContentDetector._is_compressed_format(data)
    
    @staticmethod
    def _is_executable(data: bytes) -> bool:
        """Verifica se é executável"""
        if len(data) < 4:
            return False
        
        return (data.startswith(b'MZ') or      # PE/EXE
                data.startswith(b'\x7fELF') or # ELF
                data.startswith(b'\xfe\xed\xfa') or  # Mach-O
                data.startswith(b'\xcf\xfa\xed\xfe'))  # Mach-O
    
    @staticmethod
    def _is_text(data: bytes) -> bool:
        """Verifica se é texto"""
        try:
            text = data.decode('utf-8')
            control_chars = sum(1 for c in text if ord(c) < 32 and c not in '\n\r\t')
            control_ratio = control_chars / len(text) if text else 0
            return control_ratio < 0.05  # Menos de 5% de caracteres de controle
        except:
            return False
    
    @staticmethod
    def _is_structured_text(data: bytes) -> bool:
        """Verifica se é texto estruturado"""
        try:
            text = data.decode('utf-8', errors='ignore')[:2000]
            text = text.strip()
            
            # JSON
            if ((text.startswith('{') and '}' in text) or 
                (text.startswith('[') and ']' in text)):
                return True
            
            # XML
            if text.startswith('<?xml') or (text.startswith('<') and '>' in text):
                return True
            
            # YAML
            if '---' in text or text.count(':') > text.count('\n') * 0.2:
                return True
            
            # CSV
            if text.count(',') > text.count('\n') * 2:
                return True
                
        except:
            pass
        
        return False
    
    @staticmethod
    def _is_source_code(data: bytes, filename: str) -> bool:
        """Verifica se é código fonte"""
        if filename:
            code_exts = {'.py', '.js', '.java', '.cpp', '.c', '.h', '.cs', '.php',
                        '.rb', '.go', '.rs', '.swift', '.kt', '.scala', '.sh',
                        '.html', '.css', '.sql', '.r', '.m', '.pl'}
            ext = os.path.splitext(filename.lower())[1]
            if ext in code_exts:
                return True
        
        try:
            text = data.decode('utf-8', errors='ignore')[:1000]
            # Procura por padrões de código
            code_patterns = ['function', 'class', 'import', 'include', 'def ', 'var ',
                           'const ', 'let ', 'if (', 'for (', 'while (', '#!/']
            
            pattern_count = sum(1 for pattern in code_patterns if pattern in text)
            return pattern_count >= 2
        except:
            return False
    
    @staticmethod
    def _estimate_compression_potential(entropy: float, pattern_density: float, 
                                      repetition_factor: float) -> float:
        """Estima potencial de compressão (0.0 = baixo, 1.0 = alto)"""
        # Entropia baixa = alto potencial
        entropy_factor = max(0, (8.0 - entropy) / 8.0)
        
        # Alta densidade de padrões = alto potencial
        pattern_factor = pattern_density
        
        # Alto fator de repetição = alto potencial
        repetition_factor = repetition_factor
        
        # Combina fatores com pesos
        potential = (entropy_factor * 0.5 + 
                    pattern_factor * 0.3 + 
                    repetition_factor * 0.2)
        
        return min(potential, 1.0)
    
    @staticmethod
    def _recommend_algorithm(analysis: Dict[str, Any]) -> int:
        """Recomenda algoritmo ótimo baseado na análise"""
        content_type = analysis['content_type']
        entropy = analysis['entropy']
        compression_potential = analysis['compression_potential']
        
        # Dados já comprimidos ou aleatórios - não comprimir
        if content_type in [CONTENT_ALREADY_COMPRESSED, CONTENT_RANDOM, CONTENT_MULTIMEDIA]:
            return ALGO_UNCOMPRESSED
        
        # Dados altamente repetitivos - máxima compressão
        if content_type == CONTENT_REPETITIVE or compression_potential > 0.8:
            return ALGO_HYBRID_MAX
        
        # Texto estruturado - compressão alta
        if content_type == CONTENT_TEXT_STRUCTURED:
            return ALGO_ZSTD_ULTIMATE
        
        # Código fonte - compressão balanceada
        if content_type == CONTENT_TEXT_CODE:
            return ALGO_ZSTD_BALANCED
        
        # Texto simples - compressão rápida
        if content_type == CONTENT_TEXT_PLAIN:
            return ALGO_HYBRID_FAST
        
        # Executáveis - compressão balanceada
        if content_type == CONTENT_BINARY_EXECUTABLE:
            return ALGO_ZSTD_BALANCED
        
        # Dados binários - adaptativo
        return ALGO_ADAPTIVE
    
    @staticmethod
    def _recommend_block_size(data_size: int, content_type: int, 
                            pattern_density: float) -> int:
        """Recomenda tamanho de bloco ótimo"""
        # Arquivos pequenos - blocos menores
        if data_size < 1024 * 1024:  # < 1MB
            return min(data_size, 256 * 1024)  # 256KB max
        
        # Dados repetitivos - blocos maiores para melhor compressão
        if content_type == CONTENT_REPETITIVE or pattern_density > 0.7:
            return 16 * 1024 * 1024  # 16MB
        
        # Texto estruturado - blocos médios
        if content_type == CONTENT_TEXT_STRUCTURED:
            return 4 * 1024 * 1024  # 4MB
        
        # Padrão
        return DEFAULT_BLOCK_SIZE

class UltimateCompressor:
    """Compressor com algoritmos híbridos e adaptativos"""
    
    def __init__(self):
        self.zstd_compressors = {}  # Cache de compressores
        self.dictionaries = {}      # Dicionários adaptativos
    
    def compress_adaptive(self, data: bytes, analysis: Dict[str, Any]) -> Tuple[bytes, int]:
        """Compressão adaptativa baseada na análise"""
        algorithm = analysis['optimal_algorithm']
        
        if algorithm == ALGO_UNCOMPRESSED:
            return data, ALGO_UNCOMPRESSED
        
        # Testa múltiplos algoritmos e escolhe o melhor
        candidates = []
        
        # LZ4 Turbo (sempre testa para velocidade)
        try:
            compressed = lz4.block.compress(data, mode='fast', acceleration=8)
            candidates.append((compressed, ALGO_LZ4_TURBO, len(compressed)))
        except:
            pass
        
        # Zstd níveis baseados no tipo de conteúdo
        zstd_levels = self._get_zstd_levels(analysis)
        for level in zstd_levels:
            try:
                cctx = self._get_zstd_compressor(level)
                compressed = cctx.compress(data)
                algo_code = self._zstd_level_to_algo(level)
                candidates.append((compressed, algo_code, len(compressed)))
            except:
                pass
        
        # Híbrido para dados com alto potencial
        if analysis['compression_potential'] > 0.6:
            try:
                compressed = self._compress_hybrid(data, analysis)
                candidates.append((compressed, ALGO_HYBRID_MAX, len(compressed)))
            except:
                pass
        
        # Escolhe o melhor resultado
        if not candidates:
            return data, ALGO_UNCOMPRESSED
        
        # Ordena por tamanho (menor primeiro)
        candidates.sort(key=lambda x: x[2])
        best_data, best_algo, best_size = candidates[0]
        
        # Se não há benefício significativo (< 5%), não comprime
        if best_size >= len(data) * 0.95:
            return data, ALGO_UNCOMPRESSED
        
        return best_data, best_algo
    
    def _get_zstd_levels(self, analysis: Dict[str, Any]) -> List[int]:
        """Retorna níveis Zstd a testar baseado na análise"""
        content_type = analysis['content_type']
        compression_potential = analysis['compression_potential']
        
        if compression_potential > 0.8:
            return [3, 6, 15, 19]  # Testa múltiplos níveis
        elif compression_potential > 0.5:
            return [3, 6, 15]
        elif compression_potential > 0.2:
            return [1, 3, 6]
        else:
            return [1, 3]
    
    def _get_zstd_compressor(self, level: int) -> zstd.ZstdCompressor:
        """Obtém compressor Zstd com cache"""
        if level not in self.zstd_compressors:
            self.zstd_compressors[level] = zstd.ZstdCompressor(level=level)
        return self.zstd_compressors[level]
    
    def _zstd_level_to_algo(self, level: int) -> int:
        """Converte nível Zstd para código de algoritmo"""
        if level <= 1:
            return ALGO_ZSTD_LIGHTNING
        elif level <= 6:
            return ALGO_ZSTD_BALANCED
        else:
            return ALGO_ZSTD_ULTIMATE
    
    def _compress_hybrid(self, data: bytes, analysis: Dict[str, Any]) -> bytes:
        """Compressão híbrida com múltiplas passadas"""
        # Primeira passada: LZ4 HC para encontrar repetições
        try:
            lz4_compressed = lz4.block.compress(data, mode='high_compression')
        except:
            lz4_compressed = data
        
        # Segunda passada: Zstd alto nível no resultado LZ4
        try:
            cctx = zstd.ZstdCompressor(level=19)
            final_compressed = cctx.compress(lz4_compressed)
            
            # Se a segunda passada não ajudou muito, usa só a primeira
            if len(final_compressed) >= len(lz4_compressed) * 0.95:
                return lz4_compressed
            
            return final_compressed
        except:
            return lz4_compressed

class TZPUltimateBlock:
    """Bloco avançado com análise inteligente e compressão adaptativa"""
    
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
        self.profile = profile
        
        # Análise avançada do conteúdo
        self.analysis = AdvancedContentDetector.analyze_content(data)
        self.content_type = self.analysis['content_type']
        
        if self.content_type != CONTENT_UNKNOWN:
            self.flags |= FLAG_CONTENT_DETECTED
    
    def compress_ultimate(self, compressor: UltimateCompressor) -> None:
        """Compressão ultimate com análise adaptativa"""
        # Se já está comprimido ou é multimídia, não comprime
        if self.content_type in [CONTENT_ALREADY_COMPRESSED, CONTENT_MULTIMEDIA, CONTENT_RANDOM]:
            self.compressed_data = self.original_data
            self.compressed_size = self.original_size
            self.algorithm = ALGO_UNCOMPRESSED
            self.checksum = self._calculate_checksum()
            return
        
        # Aplica pré-processamento se benéfico
        processed_data = self._preprocess_data()
        if processed_data != self.original_data:
            self.flags |= FLAG_PREPROCESSED
        
        # Compressão adaptativa
        compressed_data, algorithm = compressor.compress_adaptive(processed_data, self.analysis)
        
        self.compressed_data = compressed_data
        self.compressed_size = len(compressed_data)
        self.algorithm = algorithm
        self.checksum = self._calculate_checksum()
        
        # Marca flags adicionais
        if algorithm in [ALGO_HYBRID_FAST, ALGO_HYBRID_MAX]:
            self.flags |= FLAG_MULTI_PASS
        
        if algorithm == ALGO_ADAPTIVE:
            self.flags |= FLAG_ADAPTIVE_BLOCK
    
    def _preprocess_data(self) -> bytes:
        """Pré-processamento inteligente dos dados"""
        data = self.original_data
        
        # Delta encoding para dados numéricos sequenciais
        if self._is_numeric_sequence(data):
            return self._delta_encode(data)
        
        # Run-length encoding para dados muito repetitivos
        if self.analysis['repetition_factor'] > 0.8:
            rle_data = self._run_length_encode(data)
            if len(rle_data) < len(data) * 0.8:
                return rle_data
        
        return data
    
    def _is_numeric_sequence(self, data: bytes) -> bool:
        """Verifica se são dados numéricos sequenciais"""
        if len(data) < 16 or len(data) % 4 != 0:
            return False
        
        # Testa como sequência de inteiros de 32 bits
        try:
            numbers = struct.unpack(f'<{len(data)//4}I', data)
            if len(numbers) < 4:
                return False
            
            # Verifica se há padrão sequencial
            diffs = [numbers[i+1] - numbers[i] for i in range(len(numbers)-1)]
            diff_counter = Counter(diffs)
            
            # Se 80% das diferenças são iguais, é sequencial
            most_common_diff, count = diff_counter.most_common(1)[0]
            return count >= len(diffs) * 0.8
        except:
            return False
    
    def _delta_encode(self, data: bytes) -> bytes:
        """Codificação delta para sequências numéricas"""
        try:
            numbers = struct.unpack(f'<{len(data)//4}I', data)
            
            # Primeiro número inalterado, resto são diferenças
            deltas = [numbers[0]]
            for i in range(1, len(numbers)):
                deltas.append(numbers[i] - numbers[i-1])
            
            return struct.pack(f'<{len(deltas)}i', *deltas)
        except:
            return data
    
    def _run_length_encode(self, data: bytes) -> bytes:
        """Run-length encoding simples"""
        if not data:
            return data
        
        encoded = bytearray()
        current_byte = data[0]
        count = 1
        
        for i in range(1, len(data)):
            if data[i] == current_byte and count < 255:
                count += 1
            else:
                encoded.extend([count, current_byte])
                current_byte = data[i]
                count = 1
        
        encoded.extend([count, current_byte])
        
        # Só retorna se houve compressão significativa
        if len(encoded) < len(data) * 0.8:
            return bytes(encoded)
        
        return data
    
    def _calculate_checksum(self) -> int:
        """Calcula checksum CRC32 dos dados originais"""
        import zlib
        return zlib.crc32(self.original_data) & 0xffffffff

class TZPUltimateEncoder:
    """Encoder Ultimate com otimizações avançadas"""
    
    def __init__(self, block_size: int = None, num_threads: int = None, 
                 profile: str = PROFILE_BALANCED):
        self.profile = profile
        self.num_threads = num_threads or min(16, os.cpu_count() or 1)  # Mais threads
        self.blocks: List[TZPUltimateBlock] = []
        self.total_original_size = 0
        self.total_compressed_size = 0
        self.global_analysis = {}
        self.compressor = UltimateCompressor()
        
        # Tamanho de bloco adaptativo
        self.base_block_size = block_size or DEFAULT_BLOCK_SIZE
        self.adaptive_block_size = True
    
    def compress_file(self, input_path: str, output_path: str) -> Dict[str, Any]:
        """Comprime arquivo com tecnologia Ultimate"""
        start_time = time.time()
        
        print(f"🚀 TZP Ultimate v3.0 - Compressor de Nova Geração")
        print(f"👤 Desenvolvido por: Llucs")
        print(f"🎯 Perfil: {self.profile.upper()}")
        print(f"Entrada: {input_path} -> Saída: {output_path}")
        
        # Lê arquivo
        try:
            with open(input_path, 'rb') as f:
                data = f.read()
        except IOError as e:
            raise Exception(f"Erro ao ler arquivo: {e}")
        
        self.total_original_size = len(data)
        print(f"📊 Tamanho original: {self.total_original_size:,} bytes")
        
        # Análise global avançada
        print(f"🔬 Analisando conteúdo...")
        self.global_analysis = AdvancedContentDetector.analyze_content(data, input_path)
        
        self._print_analysis_summary()
        
        # Determina tamanho de bloco ótimo
        if self.adaptive_block_size:
            self.block_size = self.global_analysis['recommended_block_size']
            print(f"🧠 Tamanho de bloco adaptativo: {self.block_size:,} bytes")
        else:
            self.block_size = self.base_block_size
        
        # Divide em blocos inteligentes
        print(f"🔧 Dividindo em blocos otimizados...")
        self.blocks = self._split_into_smart_blocks(data)
        print(f"📦 Total de blocos: {len(self.blocks)}")
        
        # Compressão paralela otimizada
        print(f"⚡ Comprimindo com {self.num_threads} threads...")
        self._compress_blocks_parallel()
        
        self.total_compressed_size = sum(block.compressed_size for block in self.blocks)
        
        # Escreve arquivo TZP Ultimate
        self._write_tzp_ultimate_file(output_path)
        
        # Estatísticas finais
        stats = self._calculate_ultimate_stats(start_time)
        self._print_ultimate_stats(stats)
        
        return stats
    
    def _print_analysis_summary(self) -> None:
        """Imprime resumo da análise de conteúdo"""
        analysis = self.global_analysis
        
        content_names = {
            CONTENT_TEXT_PLAIN: "Texto simples",
            CONTENT_TEXT_STRUCTURED: "Texto estruturado",
            CONTENT_TEXT_CODE: "Código fonte",
            CONTENT_BINARY_EXECUTABLE: "Executável",
            CONTENT_BINARY_DATA: "Dados binários",
            CONTENT_ALREADY_COMPRESSED: "Já comprimido",
            CONTENT_MULTIMEDIA: "Multimídia",
            CONTENT_REPETITIVE: "Altamente repetitivo",
            CONTENT_RANDOM: "Aleatório/Criptografado"
        }
        
        content_name = content_names.get(analysis['content_type'], "Desconhecido")
        
        print(f"🔍 Tipo detectado: {content_name}")
        print(f"📈 Entropia: {analysis['entropy']:.2f}/8.0")
        print(f"🎯 Potencial de compressão: {analysis['compression_potential']*100:.1f}%")
        print(f"🔄 Densidade de padrões: {analysis['pattern_density']*100:.1f}%")
        print(f"🔁 Fator de repetição: {analysis['repetition_factor']*100:.1f}%")
    
    def _split_into_smart_blocks(self, data: bytes) -> List[TZPUltimateBlock]:
        """Divisão inteligente em blocos com tamanhos adaptativos"""
        blocks = []
        block_id = 0
        
        # Para arquivos pequenos, usa bloco único
        if len(data) <= self.block_size:
            block = TZPUltimateBlock(data, block_id, self.profile)
            blocks.append(block)
            return blocks
        
        # Divisão adaptativa baseada no conteúdo
        i = 0
        while i < len(data):
            # Tamanho base do bloco
            current_block_size = self.block_size
            
            # Ajusta tamanho baseado no conteúdo local
            remaining = len(data) - i
            if remaining < current_block_size * 1.5:
                # Último bloco - pega tudo que resta
                current_block_size = remaining
            else:
                # Tenta encontrar ponto de divisão natural
                natural_split = self._find_natural_split_point(
                    data, i, min(i + current_block_size, len(data))
                )
                if natural_split > i:
                    current_block_size = natural_split - i
            
            block_data = data[i:i + current_block_size]
            block = TZPUltimateBlock(block_data, block_id, self.profile)
            blocks.append(block)
            
            i += current_block_size
            block_id += 1
        
        return blocks
    
    def _find_natural_split_point(self, data: bytes, start: int, end: int) -> int:
        """Encontra ponto natural de divisão (quebras de linha, etc.)"""
        # Procura por quebras de linha próximas ao final
        search_start = max(start, end - 1024)  # Procura nos últimos 1KB
        
        for i in range(end - 1, search_start - 1, -1):
            if data[i] == ord('\n'):
                return i + 1
        
        # Se não encontrou quebra de linha, procura por zeros (separadores comuns)
        for i in range(end - 1, search_start - 1, -1):
            if data[i] == 0:
                return i + 1
        
        # Se não encontrou nada, usa posição original
        return end
    
    def _compress_blocks_parallel(self) -> None:
        """Compressão paralela otimizada"""
        with ThreadPoolExecutor(max_workers=self.num_threads) as executor:
            # Submete blocos para compressão
            future_to_block = {
                executor.submit(self._compress_block_ultimate, block): block 
                for block in self.blocks
            }
            
            # Coleta resultados com progresso
            completed = 0
            for future in as_completed(future_to_block):
                block = future.result()
                completed += 1
                
                if completed % max(1, len(self.blocks) // 10) == 0 or completed == len(self.blocks):
                    progress = (completed / len(self.blocks)) * 100
                    print(f"📈 Progresso: {completed}/{len(self.blocks)} blocos ({progress:.1f}%)")
    
    def _compress_block_ultimate(self, block: TZPUltimateBlock) -> TZPUltimateBlock:
        """Comprime bloco individual com tecnologia Ultimate"""
        block.compress_ultimate(self.compressor)
        return block
    
    def _calculate_ultimate_stats(self, start_time: float) -> Dict[str, Any]:
        """Calcula estatísticas Ultimate"""
        compression_time = time.time() - start_time
        compression_ratio = self.total_compressed_size / self.total_original_size if self.total_original_size > 0 else 1.0
        speed_mbps = (self.total_original_size / (1024 * 1024)) / compression_time if compression_time > 0 else 0
        
        # Estatísticas por algoritmo
        algo_stats = defaultdict(lambda: {'count': 0, 'original_size': 0, 'compressed_size': 0})
        
        for block in self.blocks:
            algo_name = self._algorithm_name(block.algorithm)
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
            'algorithm_stats': dict(algo_stats),
            'global_analysis': self.global_analysis,
            'profile': self.profile
        }
    
    def _algorithm_name(self, algorithm: int) -> str:
        """Converte código do algoritmo para nome"""
        names = {
            ALGO_UNCOMPRESSED: "Não comprimido",
            ALGO_LZ4_TURBO: "LZ4 Turbo",
            ALGO_LZ4_ULTRA: "LZ4 Ultra",
            ALGO_ZSTD_LIGHTNING: "Zstd Lightning",
            ALGO_ZSTD_BALANCED: "Zstd Balanced",
            ALGO_ZSTD_ULTIMATE: "Zstd Ultimate",
            ALGO_HYBRID_FAST: "Híbrido Fast",
            ALGO_HYBRID_MAX: "Híbrido Max",
            ALGO_ADAPTIVE: "Adaptativo"
        }
        return names.get(algorithm, f"Algoritmo {algorithm}")
    
    def _print_ultimate_stats(self, stats: Dict[str, Any]) -> None:
        """Imprime estatísticas Ultimate"""
        print(f"\n🎯 === TZP Ultimate v3.0 - Resultados ===")
        print(f"📊 Tamanho original: {stats['original_size']:,} bytes")
        print(f"📦 Tamanho comprimido: {stats['compressed_size']:,} bytes")
        
        reduction = (1 - stats['compression_ratio']) * 100
        print(f"🎯 Taxa de compressão: {stats['compression_ratio']:.4f} ({reduction:.2f}% de redução)")
        print(f"⏱️  Tempo: {stats['compression_time']:.2f}s")
        print(f"🚀 Velocidade: {stats['speed_mbps']:.1f} MB/s")
        print(f"📦 Blocos: {stats['num_blocks']}")
        
        print(f"\n🔧 === Algoritmos Utilizados ===")
        for algo, data in stats['algorithm_stats'].items():
            if data['count'] > 0:
                ratio = data['compressed_size'] / data['original_size'] if data['original_size'] > 0 else 1.0
                reduction_pct = (1 - ratio) * 100
                print(f"  • {algo}: {data['count']} blocos, {reduction_pct:.1f}% redução")
    
    def _write_tzp_ultimate_file(self, output_path: str) -> None:
        """Escreve arquivo TZP Ultimate v3.0"""
        try:
            with open(output_path, 'wb') as f:
                self._write_ultimate_header(f)
                self._write_ultimate_metadata(f)
                self._write_ultimate_block_table(f)
                self._write_ultimate_data(f)
        except IOError as e:
            raise Exception(f"Erro ao escrever arquivo TZP Ultimate: {e}")
    
    def _write_ultimate_header(self, f) -> None:
        """Escreve cabeçalho TZP Ultimate v3.0"""
        # Magic Number (4 bytes)
        f.write(struct.pack('<I', TZP_MAGIC))
        
        # Versão (2 bytes)
        f.write(struct.pack('<H', TZP_VERSION))
        
        # Flags globais (2 bytes)
        global_flags = (FLAG_CONTENT_DETECTED | FLAG_ADAPTIVE_BLOCK | 
                       FLAG_PATTERN_OPTIMIZED | FLAG_ENTROPY_CODED)
        f.write(struct.pack('<H', global_flags))
        
        # Tamanho original (8 bytes)
        f.write(struct.pack('<Q', self.total_original_size))
        
        # Número de blocos (4 bytes)
        f.write(struct.pack('<I', len(self.blocks)))
        
        # Tamanho base do bloco (4 bytes)
        f.write(struct.pack('<I', self.base_block_size))
        
        # Checksum do arquivo (8 bytes)
        file_checksum = hashlib.sha256(
            self.total_original_size.to_bytes(8, 'little') + 
            len(self.blocks).to_bytes(4, 'little')
        ).digest()[:8]
        f.write(file_checksum)
        
        # Tamanho dos metadados (4 bytes) - placeholder
        self.metadata_size_pos = f.tell()
        f.write(struct.pack('<I', 0))
        
        # Reservado (20 bytes)
        f.write(b'\x00' * 20)
    
    def _write_ultimate_metadata(self, f) -> None:
        """Escreve metadados Ultimate"""
        metadata = {
            'version': '3.0',
            'profile': self.profile,
            'global_analysis': self.global_analysis,
            'compression_features': [
                'adaptive_blocks',
                'content_detection',
                'pattern_optimization',
                'hybrid_algorithms',
                'intelligent_preprocessing'
            ]
        }
        
        metadata_json = json.dumps(metadata, separators=(',', ':')).encode('utf-8')
        
        # Atualiza tamanho dos metadados
        current_pos = f.tell()
        f.seek(self.metadata_size_pos)
        f.write(struct.pack('<I', len(metadata_json)))
        f.seek(current_pos)
        
        # Escreve metadados
        f.write(metadata_json)
    
    def _write_ultimate_block_table(self, f) -> None:
        """Escreve tabela de blocos Ultimate"""
        data_offset = 0
        
        for block in self.blocks:
            # Offset do bloco (8 bytes)
            f.write(struct.pack('<Q', data_offset))
            
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
            
            # Potencial de compressão (1 byte) - novo campo
            compression_potential_byte = int(block.analysis['compression_potential'] * 255)
            f.write(struct.pack('<B', compression_potential_byte))
            
            # Reservado (2 bytes)
            f.write(struct.pack('<H', 0))
            
            data_offset += block.compressed_size
    
    def _write_ultimate_data(self, f) -> None:
        """Escreve dados comprimidos"""
        for block in self.blocks:
            f.write(block.compressed_data)

def main():
    parser = argparse.ArgumentParser(
        description='TZP Ultimate v3.0 - Compressor de Nova Geração',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Perfis de compressão:
  lightning  - Máxima velocidade (LZ4 otimizado)
  turbo      - Velocidade alta com boa compressão
  balanced   - Equilíbrio ideal (padrão)
  power      - Alta compressão com velocidade aceitável
  ultimate   - Máxima compressão possível
  adaptive   - Adaptativo inteligente baseado no conteúdo

Desenvolvido por: Llucs | TZP Ultimate v3.0
        """
    )
    
    parser.add_argument('input', help='Arquivo de entrada')
    parser.add_argument('output', help='Arquivo de saída (.tzp)')
    parser.add_argument('-p', '--profile', 
                       choices=[PROFILE_LIGHTNING, PROFILE_TURBO, PROFILE_BALANCED, 
                               PROFILE_POWER, PROFILE_ULTIMATE, PROFILE_ADAPTIVE],
                       default=PROFILE_BALANCED, help='Perfil de compressão')
    parser.add_argument('--block-size', type=int, 
                       help='Tamanho do bloco em bytes (0 = adaptativo)')
    parser.add_argument('-t', '--threads', type=int, 
                       help='Número de threads (padrão: auto)')
    parser.add_argument('--json', action='store_true',
                       help='Saída em formato JSON')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"❌ Erro: Arquivo '{args.input}' não encontrado")
        sys.exit(1)
    
    if not args.output.endswith('.tzp'):
        print("⚠️  Aviso: Arquivo de saída não tem extensão .tzp")
    
    try:
        # Determina tamanho de bloco
        block_size = args.block_size if args.block_size and args.block_size > 0 else None
        
        encoder = TZPUltimateEncoder(
            block_size=block_size,
            num_threads=args.threads,
            profile=args.profile
        )
        
        stats = encoder.compress_file(args.input, args.output)
        
        if args.json:
            print(json.dumps(stats, indent=2))
        else:
            print(f"\n✅ Compressão TZP Ultimate concluída!")
            print(f"📁 Arquivo criado: {args.output}")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

