#!/usr/bin/env python3
"""
TZP Benchmark - Comparação de Performance
Compara o formato TZP com outros formatos de compressão populares

Autor: Llucs
Versão: 1.0
"""

import os
import sys
import time
import subprocess
import json
from typing import Dict, List, Any, Tuple
import argparse

class CompressionBenchmark:
    """Benchmark de compressão comparando diferentes formatos"""
    
    def __init__(self, test_files: List[str]):
        self.test_files = test_files
        self.results = {}
        
    def run_benchmark(self) -> Dict[str, Any]:
        """Executa benchmark completo"""
        print("🚀 Iniciando Benchmark de Compressão TZP vs Outros Formatos")
        print("=" * 60)
        
        for test_file in self.test_files:
            if not os.path.exists(test_file):
                print(f"⚠️  Arquivo não encontrado: {test_file}")
                continue
                
            print(f"\n📁 Testando arquivo: {os.path.basename(test_file)}")
            print(f"📊 Tamanho original: {os.path.getsize(test_file):,} bytes")
            
            file_results = {}
            
            # Testa TZP com diferentes perfis
            file_results['tzp'] = self._test_tzp_profiles(test_file)
            
            # Testa outros formatos
            file_results['gzip'] = self._test_gzip(test_file)
            file_results['lz4'] = self._test_lz4(test_file)
            file_results['zstd'] = self._test_zstd(test_file)
            file_results['7z'] = self._test_7z(test_file)
            
            self.results[test_file] = file_results
            
        return self.results
    
    def _test_tzp_profiles(self, test_file: str) -> Dict[str, Dict[str, float]]:
        """Testa TZP com diferentes perfis"""
        profiles = ['fast', 'balanced', 'deep']
        results = {}
        
        for profile in profiles:
            output_file = f"{test_file}.tzp_{profile}"
            
            try:
                # Compressão
                start_time = time.time()
                result = subprocess.run([
                    'python3', 'tzp_advanced_encoder.py',
                    '--profile', profile,
                    test_file, output_file
                ], capture_output=True, text=True, timeout=300)
                
                if result.returncode == 0:
                    compress_time = time.time() - start_time
                    compressed_size = os.path.getsize(output_file)
                    original_size = os.path.getsize(test_file)
                    
                    # Descompressão (se decoder estiver disponível)
                    decompress_time = 0
                    # TODO: Implementar teste de descompressão quando decoder estiver pronto
                    
                    results[f'tzp_{profile}'] = {
                        'compressed_size': compressed_size,
                        'compression_ratio': compressed_size / original_size,
                        'compress_time': compress_time,
                        'decompress_time': decompress_time,
                        'compress_speed_mbps': (original_size / (1024*1024)) / compress_time if compress_time > 0 else 0
                    }
                    
                    print(f"  ✅ TZP {profile}: {compressed_size:,} bytes ({100*(1-compressed_size/original_size):.1f}% redução)")
                    
                    # Remove arquivo temporário
                    os.remove(output_file)
                else:
                    print(f"  ❌ TZP {profile}: Falhou")
                    
            except Exception as e:
                print(f"  ❌ TZP {profile}: Erro - {e}")
                
        return results
    
    def _test_gzip(self, test_file: str) -> Dict[str, Dict[str, float]]:
        """Testa compressão GZIP"""
        results = {}
        levels = [1, 6, 9]  # Rápido, padrão, máximo
        
        for level in levels:
            output_file = f"{test_file}.gz_{level}"
            
            try:
                # Compressão
                start_time = time.time()
                result = subprocess.run([
                    'gzip', f'-{level}', '-c', test_file
                ], stdout=open(output_file, 'wb'), stderr=subprocess.PIPE, timeout=300)
                
                if result.returncode == 0:
                    compress_time = time.time() - start_time
                    compressed_size = os.path.getsize(output_file)
                    original_size = os.path.getsize(test_file)
                    
                    # Descompressão
                    start_time = time.time()
                    subprocess.run(['gzip', '-d', '-c', output_file], 
                                 stdout=subprocess.DEVNULL, timeout=300)
                    decompress_time = time.time() - start_time
                    
                    results[f'gzip_{level}'] = {
                        'compressed_size': compressed_size,
                        'compression_ratio': compressed_size / original_size,
                        'compress_time': compress_time,
                        'decompress_time': decompress_time,
                        'compress_speed_mbps': (original_size / (1024*1024)) / compress_time if compress_time > 0 else 0
                    }
                    
                    print(f"  ✅ GZIP-{level}: {compressed_size:,} bytes ({100*(1-compressed_size/original_size):.1f}% redução)")
                    
                    # Remove arquivo temporário
                    os.remove(output_file)
                    
            except Exception as e:
                print(f"  ❌ GZIP-{level}: Erro - {e}")
                
        return results
    
    def _test_lz4(self, test_file: str) -> Dict[str, Dict[str, float]]:
        """Testa compressão LZ4"""
        results = {}
        
        # Verifica se LZ4 está disponível
        try:
            subprocess.run(['lz4', '--version'], capture_output=True, timeout=5)
        except:
            print("  ⚠️  LZ4 não disponível")
            return results
        
        modes = ['-1', '-9']  # Rápido, alto
        
        for mode in modes:
            output_file = f"{test_file}.lz4{mode}"
            
            try:
                # Compressão
                start_time = time.time()
                result = subprocess.run([
                    'lz4', mode, test_file, output_file
                ], capture_output=True, timeout=300)
                
                if result.returncode == 0:
                    compress_time = time.time() - start_time
                    compressed_size = os.path.getsize(output_file)
                    original_size = os.path.getsize(test_file)
                    
                    # Descompressão
                    start_time = time.time()
                    subprocess.run(['lz4', '-d', output_file, '/dev/null'], 
                                 capture_output=True, timeout=300)
                    decompress_time = time.time() - start_time
                    
                    results[f'lz4{mode}'] = {
                        'compressed_size': compressed_size,
                        'compression_ratio': compressed_size / original_size,
                        'compress_time': compress_time,
                        'decompress_time': decompress_time,
                        'compress_speed_mbps': (original_size / (1024*1024)) / compress_time if compress_time > 0 else 0
                    }
                    
                    print(f"  ✅ LZ4{mode}: {compressed_size:,} bytes ({100*(1-compressed_size/original_size):.1f}% redução)")
                    
                    # Remove arquivo temporário
                    os.remove(output_file)
                    
            except Exception as e:
                print(f"  ❌ LZ4{mode}: Erro - {e}")
                
        return results
    
    def _test_zstd(self, test_file: str) -> Dict[str, Dict[str, float]]:
        """Testa compressão Zstandard"""
        results = {}
        
        # Verifica se Zstd está disponível
        try:
            subprocess.run(['zstd', '--version'], capture_output=True, timeout=5)
        except:
            print("  ⚠️  Zstd não disponível")
            return results
        
        levels = [1, 3, 19]  # Rápido, padrão, alto
        
        for level in levels:
            output_file = f"{test_file}.zst_{level}"
            
            try:
                # Compressão
                start_time = time.time()
                result = subprocess.run([
                    'zstd', f'-{level}', test_file, '-o', output_file
                ], capture_output=True, timeout=300)
                
                if result.returncode == 0:
                    compress_time = time.time() - start_time
                    compressed_size = os.path.getsize(output_file)
                    original_size = os.path.getsize(test_file)
                    
                    # Descompressão
                    start_time = time.time()
                    subprocess.run(['zstd', '-d', output_file, '-o', '/dev/null'], 
                                 capture_output=True, timeout=300)
                    decompress_time = time.time() - start_time
                    
                    results[f'zstd_{level}'] = {
                        'compressed_size': compressed_size,
                        'compression_ratio': compressed_size / original_size,
                        'compress_time': compress_time,
                        'decompress_time': decompress_time,
                        'compress_speed_mbps': (original_size / (1024*1024)) / compress_time if compress_time > 0 else 0
                    }
                    
                    print(f"  ✅ Zstd-{level}: {compressed_size:,} bytes ({100*(1-compressed_size/original_size):.1f}% redução)")
                    
                    # Remove arquivo temporário
                    os.remove(output_file)
                    
            except Exception as e:
                print(f"  ❌ Zstd-{level}: Erro - {e}")
                
        return results
    
    def _test_7z(self, test_file: str) -> Dict[str, Dict[str, float]]:
        """Testa compressão 7-Zip"""
        results = {}
        
        # Verifica se 7z está disponível
        try:
            subprocess.run(['7z'], capture_output=True, timeout=5)
        except:
            print("  ⚠️  7z não disponível")
            return results
        
        levels = [1, 5, 9]  # Rápido, padrão, máximo
        
        for level in levels:
            output_file = f"{test_file}.7z_{level}"
            
            try:
                # Compressão
                start_time = time.time()
                result = subprocess.run([
                    '7z', 'a', f'-mx={level}', output_file, test_file
                ], capture_output=True, timeout=300)
                
                if result.returncode == 0:
                    compress_time = time.time() - start_time
                    compressed_size = os.path.getsize(output_file)
                    original_size = os.path.getsize(test_file)
                    
                    # Descompressão
                    start_time = time.time()
                    subprocess.run(['7z', 'x', output_file, '-so'], 
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300)
                    decompress_time = time.time() - start_time
                    
                    results[f'7z_{level}'] = {
                        'compressed_size': compressed_size,
                        'compression_ratio': compressed_size / original_size,
                        'compress_time': compress_time,
                        'decompress_time': decompress_time,
                        'compress_speed_mbps': (original_size / (1024*1024)) / compress_time if compress_time > 0 else 0
                    }
                    
                    print(f"  ✅ 7z-{level}: {compressed_size:,} bytes ({100*(1-compressed_size/original_size):.1f}% redução)")
                    
                    # Remove arquivo temporário
                    os.remove(output_file)
                    
            except Exception as e:
                print(f"  ❌ 7z-{level}: Erro - {e}")
                
        return results
    
    def generate_report(self, output_file: str = "benchmark_report.json") -> None:
        """Gera relatório detalhado do benchmark"""
        print(f"\n📊 Gerando relatório: {output_file}")
        
        # Salva resultados em JSON
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        # Gera resumo em texto
        self._print_summary()
    
    def _print_summary(self) -> None:
        """Imprime resumo dos resultados"""
        print("\n" + "="*80)
        print("📊 RESUMO DO BENCHMARK")
        print("="*80)
        
        for test_file, file_results in self.results.items():
            print(f"\n📁 {os.path.basename(test_file)}")
            print("-" * 50)
            
            # Coleta todos os resultados
            all_results = []
            for format_family, format_results in file_results.items():
                for format_name, metrics in format_results.items():
                    all_results.append({
                        'name': format_name,
                        'ratio': metrics['compression_ratio'],
                        'compress_time': metrics['compress_time'],
                        'compress_speed': metrics['compress_speed_mbps']
                    })
            
            if not all_results:
                continue
            
            # Ordena por taxa de compressão (melhor primeiro)
            all_results.sort(key=lambda x: x['ratio'])
            
            print("🏆 Melhores taxas de compressão:")
            for i, result in enumerate(all_results[:5]):
                print(f"  {i+1}. {result['name']}: {result['ratio']:.3f} "
                      f"({100*(1-result['ratio']):.1f}% redução)")
            
            # Ordena por velocidade (mais rápido primeiro)
            all_results.sort(key=lambda x: x['compress_speed'], reverse=True)
            
            print("\n⚡ Maiores velocidades de compressão:")
            for i, result in enumerate(all_results[:5]):
                print(f"  {i+1}. {result['name']}: {result['compress_speed']:.1f} MB/s")

def main():
    parser = argparse.ArgumentParser(description='TZP Benchmark - Comparação de Performance')
    parser.add_argument('files', nargs='+', help='Arquivos para testar')
    parser.add_argument('--output', '-o', default='benchmark_report.json',
                       help='Arquivo de saída do relatório')
    
    args = parser.parse_args()
    
    # Verifica se arquivos existem
    valid_files = []
    for file_path in args.files:
        if os.path.exists(file_path):
            valid_files.append(file_path)
        else:
            print(f"⚠️  Arquivo não encontrado: {file_path}")
    
    if not valid_files:
        print("❌ Nenhum arquivo válido para testar")
        sys.exit(1)
    
    # Executa benchmark
    benchmark = CompressionBenchmark(valid_files)
    results = benchmark.run_benchmark()
    benchmark.generate_report(args.output)
    
    print(f"\n✅ Benchmark concluído! Relatório salvo em: {args.output}")

if __name__ == "__main__":
    main()

