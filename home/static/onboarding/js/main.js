/**
 * 온보딩 메인 JS
 * - 각 Step 모듈을 mount/destroy 하며, 공통 이벤트(step-success/step-previous)를 총괄
 * - 각 Step 서버 통신(API 요청 등)은 여기에서 일괄 처리합니다.
 */

import { api } from './api.js';
import { initStepper, Stepper } from './components/Stepper.js';
import { getImageUrls, getCourseHistory } from './state.js';

// Step 컴포넌트들
import * as Step1 from './steps/Step1_Account.js';
import * as Step2 from './steps/Step2_Upload.js';
import * as Step3 from './steps/Step3_AcademicInfo.js';
import * as Step4 from './steps/Step4_CourseHistory.js';
import * as Step5 from './steps/Step5_Evaluation.js';

document.addEventListener('DOMContentLoaded', () => {
  let currentStep = 1;
  const totalSteps = 5;
  let activeStepComponent = null;

  const stepContent = document.getElementById('step-content');
  const stepperEl = document.querySelector('.stepper-wrapper');
  const stepper = new Stepper(stepperEl);

  const steps = {
    1: Step1,
    2: Step2,
    3: Step3,
    4: Step4,
    5: Step5,
  };

  /**
   * 지정된 스텝 번호의 템플릿을 렌더링하고 해당 Step 모듈을 mount 합니다.
   * 이전에 활성화된 Step이 있다면 destroy를 호출해 리소스를 해제합니다.
   * @param {number} stepNumber
   */
  function renderStep(stepNumber) {
    // 이전 컴포넌트 정리
    if (activeStepComponent?.destroy) {
      try { activeStepComponent.destroy(); } catch (_) {}
    }

    currentStep = stepNumber;
    stepper.setActive(currentStep);

    // 템플릿 교체
    stepContent.innerHTML = '';
    const template = document.getElementById(`step-${currentStep}-template`);
    if (!template) return;
    stepContent.appendChild(template.content.cloneNode(true));

    // 새 컴포넌트 mount
    const StepModule = steps[currentStep];
    if (StepModule?.mount) {
      activeStepComponent = StepModule;
      StepModule.mount(stepContent);
    }
  }

  // 자식 컴포넌트가 올리는 내비게이션 이벤트 처리
  /**
   * step-success 이벤트는 각 스텝이 완료되었을 때 발생합니다.
   * 이 이벤트는 스텝별로 서버 통신을 처리하고, 다음 스텝으로 이동합니다.
   */
  stepContent.addEventListener('step-success', async (e) => {

    // Step 3에서는 학사 정보 저장 요청을 수행
    if (currentStep === 3) {
      const info = e.detail;
      try {
        const payload = {
          college: info.college,
          department: info.department,
          student_id: info.studentId,
          name: info.name,
          year: info.year,
          completed_semesters: info.completedSemesters,
          curriculum_year: info.curriculumYear,
        };
        const resp = await api.saveAcademicInfo(payload);
        if (resp.status !== 'success') return; // TODO: 통합 알림 시스템 연동
      } catch (_) { return; }
    }

    // Step 4에서는 수강 이력(과목/성적) 저장 요청을 수행
    if (currentStep === 4) {
      try {
        // 저장은 course_id와 grade
        const courses = getCourseHistory().map(c => ({ course_id: c.course_id ?? c.id, grade: c.grade }));
        const resp = await api.saveTranscripts(courses);
        if (resp.status !== 'success') return; // TODO: 통합 알림 시스템 연동
      } catch (_) { return; }
    }

    if (currentStep < totalSteps) {
      renderStep(currentStep + 1);
    } else {
      // Step 5 완료 후 대시보드(홈)로 이동
      window.location.href = '/dashboard/';
    }
  });

  /**
   * step-previous 이벤트는 이전 스텝으로 이동할 때 발생합니다.
   */
  stepContent.addEventListener('step-previous', () => {
    if (currentStep > 1) renderStep(currentStep - 1);
  });

  // 시작
  renderStep(1);
});