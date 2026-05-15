\# Codex 기본 지시문



이 저장소는 사용자의 개인 개발 작업공간이다.



\## 실제 저장소 경로



GitHub와 연결된 실제 저장소 경로는 다음과 같다.



C:\\dev\\projects\\Tilon



Codex는 기본적으로 이 경로 안에서 작업한다.



\## C:\\dev 전체 폴더 역할



C:\\dev\\projects\\Tilon

\- GitHub와 연결된 실제 개발 저장소

\- 코드, 문서, 배포 파일, Git 관리 대상 파일만 저장한다.



C:\\dev\\logs

\- Codex 실행 로그, 터미널 기록, 임시 메모 저장 위치

\- GitHub에 직접 올리지 않는다.

\- 필요한 내용만 C:\\dev\\projects\\Tilon\\docs\\logs 또는 docs\\작업로그.md에 정리한다.



C:\\dev\\sandbox

\- 임시 테스트, 실험 코드, 일회성 파일 저장 위치

\- GitHub에 직접 올리지 않는다.

\- 검증 완료된 파일만 C:\\dev\\projects\\Tilon로 옮긴다.



C:\\dev\\scripts

\- PC 전체에서 공통으로 쓰는 개인 로컬 스크립트 보관소

\- GitHub 관리 대상이 아니다.

\- 재사용 가치가 있는 스크립트만 C:\\dev\\projects\\Tilon\\scripts로 복사한다.



C:\\dev\\vm

\- VM 관련 파일, ISO, VHDX, qcow2, 테스트 자료 저장 위치

\- GitHub에 올리지 않는다.

\- VM 관련 문서나 절차만 C:\\dev\\projects\\Tilon\\docs에 정리한다.



\## 작업 규칙



1\. 기본 작업 위치는 C:\\dev\\projects\\Tilon 이다.

2\. 저장소 밖의 C:\\dev\\logs, C:\\dev\\sandbox, C:\\dev\\scripts, C:\\dev\\vm은 로컬 작업공간이다.

3\. 저장소 밖 파일을 수정하거나 생성해야 할 때는 먼저 사용자에게 목적을 설명한다.

4\. 비밀번호, 토큰, 인증서, 서버 접속정보를 코드에 직접 저장하지 않는다.

5\. 필요한 환경변수는 .env.example에만 예시로 작성한다.

6\. VM 이미지, ISO, VHDX, qcow2, 백업파일은 Git에 추가하지 않는다.

7\. 기능 개발 후 실행 방법을 README.md 또는 docs에 기록한다.

8\. 오류가 발생하면 원인, 해결방법, 재현방법을 docs\\테스트결과.md에 기록한다.

9\. 모든 작업 내용은 docs\\작업로그.md에 날짜별로 기록한다.

10\. 사용자가 승인하기 전에는 git push를 하지 않는다.

11\. 작업 완료 후 변경 파일 목록, 테스트 결과, 다음 작업 추천을 알려준다.



\## 폴더 사용 기준



apps

\- 웹 프로그램, 간단한 앱, 테스트용 서비스



scripts

\- GitHub에 올릴 PowerShell, CMD, Bash 스크립트



docs

\- 요구사항, 작업로그, 테스트결과, 서버배포, 사용자매뉴얼



prompts

\- Codex에게 줄 지시문과 작업 템플릿



deploy

\- 서버 배포용 파일, docker-compose, nginx 설정, 배포 스크립트



tools

\- 개발 보조 도구, 변환 스크립트, 자동화 도구

