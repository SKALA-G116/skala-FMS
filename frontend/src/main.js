/*
==============================================================================
FMS_FILE_SPEC
main.js - Vue 애플리케이션 main
==============================================================================
설명:
    - Vue 애플리케이션 main
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

    상세 Git 이력: git log --follow -- frontend/src/main.js
    공통 규칙: doc/file-header-policy.md
==============================================================================
*/
import {createApp} from 'vue';import {createRouter,createWebHistory} from 'vue-router';import App from './App.vue';import Dashboard from './views/Dashboard.vue';import Documents from './views/Documents.vue';import Reviews from './views/Reviews.vue';import Catalog from './views/Catalog.vue';import Jobs from './views/Jobs.vue';import Reference from './views/Reference.vue';import CreateReview from './views/CreateReview.vue';import Prices from './views/Prices.vue';import Sources from './views/Sources.vue';import WorkbookTable from './components/WorkbookTable.vue';import ExtractionReview from './views/ExtractionReview.vue';import FoodCatalog from './views/FoodCatalog.vue';import './style.css';
const router=createRouter({history:createWebHistory(),routes:[{path:'/analysis-runs/:id/review',component:ExtractionReview},{path:'/',component:Dashboard},{path:'/login',component:Dashboard},{path:'/documents/:id?',component:Documents},{path:'/materials/tables',component:WorkbookTable},{path:'/collection',component:Sources},{path:'/reviews/new',component:CreateReview},{path:'/reviews/:id?',component:Reviews},{path:'/prices',component:Prices},{path:'/products',component:FoodCatalog},{path:'/products/:id',component:Catalog},{path:'/products/:id/history',component:Catalog},{path:'/jobs/:id?',component:Jobs},{path:'/evidence/:id',component:Reference},{path:'/history/:id',component:Reference}]});createApp(App).use(router).mount('#app');
