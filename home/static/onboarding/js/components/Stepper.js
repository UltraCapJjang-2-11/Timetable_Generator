// components/Stepper.js

/**
 * 스텝 진행 상태를 표시/제어하는 스텝퍼 컴포넌트.
 * 컨테이너 내부의 `.stepper-item` 요소를 대상으로 활성(active)/완료(completed) 클래스를 토글합니다.
 */
export class Stepper {
  /**
   * @param {HTMLElement} stepperElement - 스텝퍼 루트 요소. 내부에 `data-step` 속성을 가진 `.stepper-item`들이 있어야 합니다.
   */
  constructor(stepperElement) {
    this.root = stepperElement;
    this.items = Array.from(this.root?.querySelectorAll('.stepper-item') || []);
  }

  /**
   * 주어진 스텝 번호에 맞춰 항목들의 active/completed 상태를 갱신합니다.
   * @param {number} stepNumber - 활성화할 현재 스텝(1-based 권장)
   */
  setActive(stepNumber) {
    if (!this.items.length) return;
    this.items.forEach((item) => {
      const step = parseInt(item.dataset.step, 10);
      item.classList.remove('active', 'completed');
      if (step < stepNumber) {
        item.classList.add('completed');
      } else if (step === stepNumber) {
        item.classList.add('active');
      }
    });
  }
}

/**
 * Stepper 인스턴스를 생성하는 헬퍼.
 * @param {HTMLElement} stepperElement
 * @returns {Stepper}
 */
export function initStepper(stepperElement) {
  return new Stepper(stepperElement);
}


