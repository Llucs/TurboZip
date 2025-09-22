#!/usr/bin/env python3
"""
TZP - Turbo Zip Command Line Tool
Ferramenta unificada de compressão/descompressão para o formato .tzp

Autor: Llucs
Versão: 2.0
"""

import os
import sys
import argparse
import json
from typing import Dict, Any, List

# Importa os módulos TZP
try:
    from tzp_advanced_encoder import TZPAdvancedEncoder, PROFILE_FAST, PROFILE_BALANCED, PROFILE_DEEP, PROFILE_MAX
    from tzp_decoder import TZPDecoder
except ImportError:
    print("❌ Erro: Módulos TZP não encontrados. Certifique-se de que os arquivos estão no mesmo diretório.")
    sys.exit(1)

class TZPCommandLine:
    """Interface de linha de comando para TZP"""
    
    def __init__(self):
        self.version = "2.0"
        self.author = "Llucs"
    
    def compress(self, args) -> None:
        """Comprime arquivo(s) para formato TZP"""
        if not os.path.exists(args.input):
            print(f"❌ Erro: Arquivo '{args.input}' não encontrado")
            sys.exit(1)
        
        # Define arquivo de saída se não especificado
        if not args.output:
            args.output = args.input + '.tzp'
        
        try:
            encoder = TZPAdvancedEncoder(
                block_size=args.block_size,
                num_threads=args.threads,
                profile=args.profile
            )
            
            print(f"🚀 TZP v{self.version} - Compressor Turbo Zip")
            print(f"👤 Desenvolvido por: {self.author}")
            print()
            
            stats = encoder.compress_file(args.input, args.output)
            
            if args.json:
                print(json.dumps(stats, indent=2))
            
        except Exception as e:
            print(f"❌ Erro durante compressão: {e}")
            sys.exit(1)
    
    def decompress(self, args) -> None:
        """Descomprime arquivo TZP"""
        if not os.path.exists(args.input):
            print(f"❌ Erro: Arquivo '{args.input}' não encontrado")
            sys.exit(1)
        
        if not args.input.endswith('.tzp'):
            print("⚠️  Aviso: Arquivo não tem extensão .tzp")
        
        # Define arquivo de saída se não especificado
        if not args.output:
            if args.input.endswith('.tzp'):
                args.output = args.input[:-4]  # Remove .tzp
            else:
                args.output = args.input + '.extracted'
        
        try:
            decoder = TZPDecoder(num_threads=args.threads)
            
            print(f"🚀 TZP v{self.version} - Descompressor Turbo Zip")
            print(f"👤 Desenvolvido por: {self.author}")
            print()
            
            stats = decoder.decompress_file(args.input, args.output)
            
            if args.json:
                print(json.dumps(stats, indent=2))
            
        except Exception as e:
            print(f"❌ Erro durante descompressão: {e}")
            sys.exit(1)
    
    def info(self, args) -> None:
        """Mostra informações sobre arquivo TZP"""
        if not os.path.exists(args.input):
            print(f"❌ Erro: Arquivo '{args.input}' não encontrado")
            sys.exit(1)
        
        try:
            decoder = TZPDecoder()
            info = decoder.get_info(args.input)
            
            print(f"🚀 TZP v{self.version} - Informações do Arquivo")
            print(f"👤 Desenvolvido por: {self.author}")
            print()
            
            if args.json:
                print(json.dumps(info, indent=2))
            else:
                self._print_info(info)
            
        except Exception as e:
            print(f"❌ Erro ao ler arquivo: {e}")
            sys.exit(1)
    
    def _print_info(self, info: Dict[str, Any]) -> None:
        """Imprime informações formatadas"""
        print(f"📁 Arquivo: {info['file_path']}")
        print(f"📋 Versão TZP: {info['version']}")
        print(f"📊 Tamanho original: {info['original_size']:,} bytes")
        print(f"📦 Tamanho comprimido: {info['compressed_size']:,} bytes")
        print(f"🎯 Taxa de compressão: {info['compression_ratio']:.3f} ({100 * (1 - info['compression_ratio']):.1f}% de redução)")
        print(f"🧩 Número de blocos: {info['num_blocks']}")
        print(f"📏 Tamanho do bloco: {info['block_size']:,} bytes")
        print(f"🔒 Checksum: {'Sim' if info['has_checksum'] else 'Não'}")
        
        if info['algorithm_stats']:
            print(f"\n🔧 Algoritmos utilizados:")
            for algo, stats in info['algorithm_stats'].items():
                ratio = stats['compressed_size'] / stats['original_size'] if stats['original_size'] > 0 else 1.0
                print(f"  • {algo}: {stats['count']} blocos, taxa {ratio:.3f}")
    
    def benchmark(self, args) -> None:
        """Executa benchmark de compressão"""
        from benchmark_tzp import CompressionBenchmark
        
        files = args.files
        valid_files = [f for f in files if os.path.exists(f)]
        
        if not valid_files:
            print("❌ Nenhum arquivo válido para benchmark")
            sys.exit(1)
        
        print(f"🚀 TZP v{self.version} - Benchmark de Compressão")
        print(f"👤 Desenvolvido por: {self.author}")
        print()
        
        benchmark = CompressionBenchmark(valid_files)
        results = benchmark.run_benchmark()
        benchmark.generate_report(args.output)
    
    def version_info(self) -> None:
        """Mostra informações de versão"""
        print(f"🚀 TZP - Turbo Zip v{self.version}")
        print(f"👤 Desenvolvido por: {self.author}")
        print(f"📅 Setembro 2025")
        print()
        print("🎯 Formato de compressão híbrido e adaptativo")
        print("⚡ Super rápido, eficiente e alta taxa de compressão")
        print("🔧 Detecção automática de conteúdo e perfis otimizados")
        print()
        print("📖 Perfis disponíveis:")
        print("  • fast     - Máxima velocidade (LZ4)")
        print("  • balanced - Equilíbrio velocidade/compressão (padrão)")
        print("  • deep     - Alta compressão (Zstd níveis altos)")
        print("  • max      - Máxima compressão (Zstd nível 22)")

def main():
    cli = TZPCommandLine()
    
    parser = argparse.ArgumentParser(
        description='TZP - Turbo Zip: Compressor híbrido e adaptativo',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Exemplos de uso:
  tzp compress arquivo.txt                    # Comprime com perfil padrão
  tzp compress -p fast arquivo.txt           # Compressão rápida
  tzp compress -p deep arquivo.txt -o saida.tzp  # Alta compressão
  tzp decompress arquivo.tzp                 # Descomprime arquivo
  tzp info arquivo.tzp                       # Mostra informações
  tzp benchmark *.txt                        # Benchmark de arquivos

Desenvolvido por: {cli.author} | Versão: {cli.version}
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Comandos disponíveis')
    
    # Comando compress
    compress_parser = subparsers.add_parser('compress', help='Comprime arquivo para formato TZP')
    compress_parser.add_argument('input', help='Arquivo de entrada')
    compress_parser.add_argument('-o', '--output', help='Arquivo de saída (.tzp)')
    compress_parser.add_argument('-p', '--profile', 
                               choices=[PROFILE_FAST, PROFILE_BALANCED, PROFILE_DEEP, PROFILE_MAX],
                               default=PROFILE_BALANCED, help='Perfil de compressão')
    compress_parser.add_argument('--block-size', type=int, default=4*1024*1024,
                               help='Tamanho do bloco em bytes')
    compress_parser.add_argument('-t', '--threads', type=int, help='Número de threads')
    compress_parser.add_argument('--json', action='store_true', help='Saída em formato JSON')
    
    # Comando decompress
    decompress_parser = subparsers.add_parser('decompress', help='Descomprime arquivo TZP')
    decompress_parser.add_argument('input', help='Arquivo TZP de entrada')
    decompress_parser.add_argument('-o', '--output', help='Arquivo de saída')
    decompress_parser.add_argument('-t', '--threads', type=int, help='Número de threads')
    decompress_parser.add_argument('--json', action='store_true', help='Saída em formato JSON')
    
    # Comando info
    info_parser = subparsers.add_parser('info', help='Mostra informações sobre arquivo TZP')
    info_parser.add_argument('input', help='Arquivo TZP')
    info_parser.add_argument('--json', action='store_true', help='Saída em formato JSON')
    
    # Comando benchmark
    benchmark_parser = subparsers.add_parser('benchmark', help='Executa benchmark de compressão')
    benchmark_parser.add_argument('files', nargs='+', help='Arquivos para testar')
    benchmark_parser.add_argument('-o', '--output', default='benchmark_report.json',
                                help='Arquivo de relatório')
    
    # Comando version
    version_parser = subparsers.add_parser('version', help='Mostra informações de versão')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Executa comando
    if args.command == 'compress':
        cli.compress(args)
    elif args.command == 'decompress':
        cli.decompress(args)
    elif args.command == 'info':
        cli.info(args)
    elif args.command == 'benchmark':
        cli.benchmark(args)
    elif args.command == 'version':
        cli.version_info()

if __name__ == "__main__":
    main()

