/*
==============================================================================
FMS_FILE_SPEC
vite.config.js - Vue 애플리케이션 vite.config
==============================================================================
설명:
    - Vue 애플리케이션 vite.config
입력·출력 명세:
    - 입력: 애플리케이션·라우트·상태·빌드 설정
    - 출력: 화면·공유 상태·빌드 산출물
실행 가정:
    - 설치 의존성과 생성 lock 파일은 원본 형식을 유지
작성 정보:
    - 작성자: 미지정
    - 이메일: 미지정
    - 작성일: 2026-10-21 (최초 Git 등록일 기준)
    - 라이선스: 미지정
    - 버전: 0.1.0
    - 상태: Development
변경 이력 (Revision History):
    DATE        AUTHOR      VERSION  DESCRIPTION
    --------------------------------------------------------------------
    2026-10-21  미지정      v0.1.0   최초 Git 등록 a11ef05a
    2026-10-21  미지정      v0.1.0   파일 역할·입출력·가정·이력 명세 추가

    상세 Git 이력: git log --follow -- frontend/vite.config.js
    공통 규칙: doc/file-header-policy.md
==============================================================================
*/
import { defineConfig } from 'vite';import vue from '@vitejs/plugin-vue';export default defineConfig({plugins:[vue()],server:{proxy:{'/api':'http://127.0.0.1:8100'}},build:{outDir:'dist'}})
