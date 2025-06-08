// home/js/category_dropdown.js

// 모듈 스코프에 변수를 선언만 합니다.
let $elements;

// 외부에서 사용할 수 있도록 DOM 요소를 반환하는 함수 (수정 없음)
export function getCategoryDOMElements() {
    return $elements;
}

// 현재 선택된 최하위 카테고리 ID를 반환하는 함수 (수정 없음)
export function getSelectedCategoryId() {
    return $elements.grandchildCategory.value || $elements.childCategory.value || $elements.rootCategory.value;
}


document.addEventListener('DOMContentLoaded', () => {
    // DOM이 준비된 후, 요소를 찾아 객체에 할당합니다.
    $elements = {
        categoriesData: document.getElementById('categories-data'),
        rootCategory: document.getElementById('category_root'),
        childCategory: document.getElementById('category_child'),
        grandchildCategory: document.getElementById('category_grandchild'),
        childContainer: document.getElementById('child-container'),
        grandchildContainer: document.getElementById('grandchild-container'),
        orgContainer: document.getElementById('org-container'),
        courseNameSearch: document.getElementById('course_name_search'),
    };

    // 이제 $elements.categoriesData는 null이 아닙니다.
    const allCategories = JSON.parse($elements.categoriesData.textContent);

    /**
     * 드롭다운 셀렉트 박스를 초기화합니다.
     * @param {HTMLSelectElement} selectElement
     */
    function resetSelect(selectElement) {
        selectElement.options.length = 1;
        selectElement.disabled = true;
    }

    // ... (이하 나머지 코드는 동일)

    /**
     * 조직(단과대학/학과) 관련 드롭다운을 숨기고 초기화합니다.
     */
    function hideOrgDropdowns() {
        $elements.orgContainer.style.display = 'none';
        const orgCollege = document.getElementById('college');
        const orgDept = document.getElementById('dept');
        if (orgCollege) orgCollege.value = '';
        if (orgDept) {
            orgDept.value = '';
            orgDept.disabled = true;
        }
    }

    /**
     * 주어진 부모 ID에 해당하는 카테고리 옵션을 셀렉트 박스에 추가합니다.
     * @param {HTMLSelectElement} selectElement
     * @param {string|null} parentId
     */
    function populateCategories(selectElement, parentId) {
        selectElement.options.length = 1; // 기본 옵션만 남기고 초기화
        allCategories
            .filter(c => c.parent_category_id == parentId)
            .forEach(c => selectElement.add(new Option(c.category_name, c.category_id)));
    }

    /**
     * 대분류 선택 변경 시 UI를 업데이트합니다.
     */
    function handleRootCategoryChange() {
        resetSelect($elements.childCategory);
        resetSelect($elements.grandchildCategory);
        if ($elements.courseNameSearch) $elements.courseNameSearch.value = '';

        hideOrgDropdowns();

        const rootValue = $elements.rootCategory.value;
        if (!rootValue) return;

        const rootText = $elements.rootCategory.selectedOptions[0].textContent;

        $elements.childContainer.style.display = '';
        $elements.childCategory.disabled = false;
        populateCategories($elements.childCategory, rootValue);

        if (rootText === '전공') {
            $elements.orgContainer.style.display = '';
        }
    }

    /**
     * 중분류 선택 변경 시 UI를 업데이트합니다.
     */
    function handleChildCategoryChange() {
        resetSelect($elements.grandchildCategory);
        $elements.grandchildContainer.style.display = 'none';

        const childValue = $elements.childCategory.value;
        const rootText = $elements.rootCategory.selectedOptions[0].textContent;

        if (rootText !== '교양' || !childValue) return;

        $elements.grandchildContainer.style.display = '';
        $elements.grandchildCategory.disabled = false;
        populateCategories($elements.grandchildCategory, childValue);
    }

    // --- 초기화 및 이벤트 리스너 등록 ---
    populateCategories($elements.rootCategory, null);
    $elements.rootCategory.onchange = handleRootCategoryChange;
    $elements.childCategory.onchange = handleChildCategoryChange;
});