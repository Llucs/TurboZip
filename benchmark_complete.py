#!/usr/bin/env python3
"""
Benchmark Completo TZP - Comparação de Performance
Compara TZP Stable com outros formatos de compressão

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

class CompleteBenchmark:
    """Benchmark completo de compressão"""
    
    def __init__(self, test_files: List[str]):
        self.test_files = test_files
        self.results = {}
        
    def run_complete_benchmark(self) -> Dict[str, Any]:
        """Executa benchmark completo"""
        print("🚀 Benchmark Completo TZP Stable vs Formatos Tradicionais")
        print("=" * 70)
        
        for test_file in self.test_files:
            if not os.path.exists(test_file):
                print(f"⚠️  Arquivo não encontrado: {test_file}")
                continue
                
            print(f"\n📁 Testando: {os.path.basename(test_file)}")
            original_size = os.path.getsize(test_file)
            print(f"📊 Tamanho original: {original_size:,} bytes")
            
            file_results = {}
            
            # Testa TZP Stable com todos os perfis
            file_results['tzp_stable'] = self._test_tzp_stable(test_file)
            
            # Testa formatos tradicionais
            file_results['gzip'] = self._test_gzip(test_file)
            file_results['bzip2'] = self._test_bzip2(test_file)
            file_results['xz'] = self._test_xz(test_file)
            
            self.results[test_file] = {
                'original_size': original_size,
                'results': file_results
            }
            
        return self.results
    
    def _test_tzp_stable(self, test_file: str) -> Dict[str, Dict[str, float]]:
        """Testa TZP Stable com todos os perfis"""
        profiles = ['lightning', 'fast', 'balanced', 'high', 'max']
        results = {}
        
        for profile in profiles:
            output_file = f"{test_file}.tzp_{profile}"
            
            try:
                # Compressão
                start_time = time.time()
                result = subprocess.run([
                    'python3', 'tzp_stable.py',
                    '-p', profile,
                    test_file, output_file
                ], capture_output=True, text=True, timeout=300)
                
                if result.returncode == 0:
                    compress_time = time.time() - start_time
                    compressed_size = os.path.getsize(output_file)
                    original_size = os.path.getsize(test_file)
                    
                    results[f'tzp_{profile}'] = {
                        'compressed_size': compressed_size,
                        'compression_ratio': compressed_size / original_size,
                        'compress_time': compress_time,
                        'compress_speed_mbps': (original_size / (1024*1024)) / compress_time if compress_time > 0 else 0,
                        'reduction_percent': (1 - compressed_size/original_size) * 100
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
        """Testa GZIP"""
        results = {}
        levels = [1, 6, 9]
        
        for level in levels:
            output_file = f"{test_file}.gz_{level}"
            
            try:
                # Compressão
                start_time = time.time()
                with open(output_file, 'wb') as f:
                    result = subprocess.run([
                        'gzip', f'-{level}', '-c', test_file
                    ], stdout=f, stderr=subprocess.PIPE, timeout=300)
                
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
                        'compress_speed_mbps': (original_size / (1024*1024)) / compress_time if compress_time > 0 else 0,
                        'reduction_percent': (1 - compressed_size/original_size) * 100
                    }
                    
                    print(f"  ✅ GZIP-{level}: {compressed_size:,} bytes ({100*(1-compressed_size/original_size):.1f}% redução)")
                    
                    os.remove(output_file)
                    
            except Exception as e:
                print(f"  ❌ GZIP-{level}: Erro - {e}")
                
        return results
    
    def _test_bzip2(self, test_file: str) -> Dict[str, Dict[str, float]]:
        """Testa BZIP2"""
        results = {}
        levels = [1, 6, 9]
        
        for level in levels:
            output_file = f"{test_file}.bz2_{level}"
            
            try:
                # Compressão
                start_time = time.time()
                with open(output_file, 'wb') as f:
                    result = subprocess.run([
                        'bzip2', f'-{level}', '-c', test_file
                    ], stdout=f, stderr=subprocess.PIPE, timeout=300)
                
                if result.returncode == 0:
                    compress_time = time.time() - start_time
                    compressed_size = os.path.getsize(output_file)
                    original_size = os.path.getsize(test_file)
                    
                    # Descompressão
                    start_time = time.time()
                    subprocess.run(['bzip2', '-d', '-c', output_file], 
                                 stdout=subprocess.DEVNULL, timeout=300)
                    decompress_time = time.time() - start_time
                    
                    results[f'bzip2_{level}'] = {
                        'compressed_size': compressed_size,
                        'compression_ratio': compressed_size / original_size,
                        'compress_time': compress_time,
                        'decompress_time': decompress_time,
                        'compress_speed_mbps': (original_size / (1024*1024)) / compress_time if compress_time > 0 else 0,
                        'reduction_percent': (1 - compressed_size/original_size) * 100
                    }
                    
                    print(f"  ✅ BZIP2-{level}: {compressed_size:,} bytes ({100*(1-compressed_size/original_size):.1f}% redução)")
                    
                    os.remove(output_file)
                    
            except Exception as e:
                print(f"  ❌ BZIP2-{level}: Erro - {e}")
                
        return results
    
    def _test_xz(self, test_file: str) -> Dict[str, Dict[str, float]]:
        """Testa XZ"""
        results = {}
        levels = [1, 6, 9]
        
        for level in levels:
            output_file = f"{test_file}.xz_{level}"
            
            try:
                # Compressão
                start_time = time.time()
                result = subprocess.run([
                    'xz', f'-{level}', '-c', test_file
                ], stdout=open(output_file, 'wb'), stderr=subprocess.PIPE, timeout=300)
                
                if result.returncode == 0:
                    compress_time = time.time() - start_time
                    compressed_size = os.path.getsize(output_file)
                    original_size = os.path.getsize(test_file)
                    
                    # Descompressão
                    start_time = time.time()
                    subprocess.run(['xz', '-d', '-c', output_file], 
                                 stdout=subprocess.DEVNULL, timeout=300)
                    decompress_time = time.time() - start_time
                    
                    results[f'xz_{level}'] = {
                        'compressed_size': compressed_size,
                        'compression_ratio': compressed_size / original_size,
                        'compress_time': compress_time,
                        'decompress_time': decompress_time,
                        'compress_speed_mbps': (original_size / (1024*1024)) / compress_time if compress_time > 0 else 0,
                        'reduction_percent': (1 - compressed_size/original_size) * 100
                    }
                    
                    print(f"  ✅ XZ-{level}: {compressed_size:,} bytes ({100*(1-compressed_size/original_size):.1f}% redução)")
                    
                    os.remove(output_file)
                    
            except Exception as e:
                print(f"  ❌ XZ-{level}: Erro - {e}")
                
        return results
    
    def generate_complete_report(self, output_file: str = "benchmark_complete.json") -> None:
        """Gera relatório completo"""
        print(f"\n📊 Gerando relatório completo: {output_file}")
        
        # Salva resultados em JSON
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        # Gera resumo detalhado
        self._print_detailed_summary()
    
    def _print_detailed_summary(self) -> None:
        """Imprime resumo detalhado"""
        print("\n" + "="*80)
        print("📊 RELATÓRIO COMPLETO DE BENCHMARK")
        print("="*80)
        
        for test_file, file_data in self.results.items():
            print(f"\n📁 {os.path.basename(test_file)}")
            print(f"📊 Tamanho original: {file_data['original_size']:,} bytes")
            print("-" * 60)
            
            # Coleta todos os resultados
            all_results = []
            for format_family, format_results in file_data['results'].items():
                for format_name, metrics in format_results.items():
                    all_results.append({
                        'name': format_name,
                        'ratio': metrics['compression_ratio'],
                        'reduction': metrics['reduction_percent'],
                        'speed': metrics['compress_speed_mbps'],
                        'time': metrics['compress_time'],
                        'size': metrics['compressed_size']
                    })
            
            if not all_results:
                continue
            
            # Melhores taxas de compressão
            best_compression = sorted(all_results, key=lambda x: x['ratio'])[:5]
            print("🏆 Melhores taxas de compressão:")
            for i, result in enumerate(best_compression):
                print(f"  {i+1}. {result['name']}: {result['reduction']:.2f}% "
                      f"({result['size']:,} bytes)")
            
            # Maiores velocidades
            best_speed = sorted(all_results, key=lambda x: x['speed'], reverse=True)[:5]
            print("\n⚡ Maiores velocidades:")
            for i, result in enumerate(best_speed):
                print(f"  {i+1}. {result['name']}: {result['speed']:.1f} MB/s "
                      f"({result['time']:.2f}s)")
            
            # Análise TZP vs outros
            tzp_results = [r for r in all_results if r['name'].startswith('tzp_')]
            other_results = [r for r in all_results if not r['name'].startswith('tzp_')]
            
            if tzp_results and other_results:
                best_tzp = min(tzp_results, key=lambda x: x['ratio'])
                best_other = min(other_results, key=lambda x: x['ratio'])
                
                print(f"\n🎯 TZP vs Melhor Concorrente:")
                print(f"  TZP {best_tzp['name']}: {best_tzp['reduction']:.2f}% redução")
                print(f"  {best_other['name']}: {best_other['reduction']:.2f}% redução")
                
                if best_tzp['ratio'] < best_other['ratio']:
                    improvement = (best_other['ratio'] - best_tzp['ratio']) / best_other['ratio'] * 100
                    print(f"  🏆 TZP é {improvement:.1f}% melhor!")
                else:
                    difference = (best_tzp['ratio'] - best_other['ratio']) / best_other['ratio'] * 100
                    print(f"  📊 TZP é {difference:.1f}% pior")

def main():
    parser = argparse.ArgumentParser(description='Benchmark Completo TZP')
    parser.add_argument('files', nargs='+', help='Arquivos para testar')
    parser.add_argument('--output', '-o', default='benchmark_complete.json',
                       help='Arquivo de relatório')
    
    args = parser.parse_args()
    
    # Verifica arquivos
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
    benchmark = CompleteBenchmark(valid_files)
    results = benchmark.run_complete_benchmark()
    benchmark.generate_complete_report(args.output)
    
    print(f"\n✅ Benchmark completo! Relatório: {args.output}")

if __name__ == "__main__":
    main()

