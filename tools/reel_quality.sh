#!/usr/bin/env bash
# Compara definições de codificação do Reel RBCP (só números: tamanho e SSIM/PSNR contra o original; ninguém vê o vídeo).
set -e
ffprobe -v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate,bit_rate,codec_name,profile,pix_fmt -of default=nw=1 src.mp4
ffprobe -v error -select_streams a:0 -show_entries stream=codec_name,bit_rate,sample_rate,channels -of default=nw=1 src.mp4
ffprobe -v error -show_entries format=duration,bit_rate,size -of default=nw=1 src.mp4
run() { name=$1; shift; t0=$(date +%s); ffmpeg -y -v error -i src.mp4 "$@" -an out_$name.mp4; t1=$(date +%s)
  sz=$(stat -c %s out_$name.mp4)
  m=$(ffmpeg -i out_$name.mp4 -i src.mp4 -lavfi "[0:v]settb=AVTB,setpts=PTS-STARTPTS,fps=25[a];[1:v]settb=AVTB,setpts=PTS-STARTPTS,fps=25[b];[a][b]ssim" -f null - 2>&1 | grep -o "All:[0-9.]*" | tail -1)
  echo "$name: $(echo "scale=1;$sz/1000000"|bc) MB, $m, $((t1-t0))s"; }
run atual   -c:v libx264 -preset veryfast -crf 23 -maxrate 6M -bufsize 12M -pix_fmt yuv420p -r 30
run atual25 -c:v libx264 -preset veryfast -crf 23 -maxrate 6M -bufsize 12M -pix_fmt yuv420p
run crf18s  -c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p
B=6000k
ffmpeg -y -v error -i src.mp4 -c:v libx264 -preset slow -b:v $B -pass 1 -passlogfile p -an -f null /dev/null
run 2pass6  -c:v libx264 -preset slow -b:v $B -maxrate 9M -bufsize 12M -pass 2 -passlogfile p -pix_fmt yuv420p -profile:v high
B=6000k
ffmpeg -y -v error -i src.mp4 -c:v libx264 -preset slower -tune film -b:v $B -pass 1 -passlogfile q -an -f null /dev/null
run 2pass6slower -c:v libx264 -preset slower -tune film -b:v $B -maxrate 9M -bufsize 12M -pass 2 -passlogfile q -pix_fmt yuv420p -profile:v high
