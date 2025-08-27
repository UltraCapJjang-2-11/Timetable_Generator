// [리팩터링] 공유 컴포넌트: 드롭다운 연동 + 검색 파라미터 생성만 담당

let __categoriesCache = null;

export function initializeCategoryDropdowns() {
  const $root  = document.getElementById('category_root');
  if (!$root) return;

  const $child = document.getElementById('category_child');
  const $grand = document.getElementById('category_grandchild');
  const $childBox  = document.getElementById('child-container');
  const $grandBox  = document.getElementById('grandchild-container');
  const $orgContainer = document.getElementById('org-container');
  const $courseNameSearch = document.getElementById('course_name_search');

  function resetSelect(sel){ sel.options.length = 1; sel.disabled = true; }
  function hideOrg(){
    if (!$orgContainer) return;
    $orgContainer.style.display = 'none';
    const $orgCollege = document.getElementById('college');
    const $orgDept = document.getElementById('dept');
    if($orgCollege){ $orgCollege.value = ''; }
    if($orgDept){ $orgDept.value = ''; $orgDept.disabled = true; }
    if ($courseNameSearch) $courseNameSearch.value = '';
  }

  const ensureCategories = async () => {
    if (__categoriesCache) return __categoriesCache;
    const res = await fetch('/data-manager/api/categories/');
    if (!res.ok) throw new Error('카테고리 API 오류');
    const json = await res.json();
    __categoriesCache = json.data;
    return __categoriesCache;
  };

  ensureCategories().then(categoriesData => {
    // 루트 채우기
    categoriesData.filter(c => c.parent_category_id === null)
      .forEach(c => $root.add(new Option(c.category_name, c.category_id)));

    $root.onchange = () => {
      resetSelect($child); resetSelect($grand);
      $childBox.style.display = 'none';
      $grandBox.style.display = 'none';
      if ($courseNameSearch) $courseNameSearch.value = '';

      hideOrg();

      if(!$root.value) return;
      const rootText = $root.selectedOptions[0].textContent;

      $childBox.style.display = '';
      $child.disabled = false;
      categoriesData.filter(c => c.parent_category_id == $root.value)
          .forEach(c => $child.add(new Option(c.category_name, c.category_id)));

      if(rootText === '전공'){
        if ($orgContainer) { $orgContainer.style.display = ''; }
        if (typeof initializeOrgDropdowns === 'function') {
          initializeOrgDropdowns();
        }
      } else if(rootText === '교양'){
        $grandBox.style.display = '';
      }
    };

    $child.onchange = () => {
      resetSelect($grand);
      $grandBox.style.display='none';
      if($root.selectedOptions[0].text !== '교양' || !$child.value) return;

      $grandBox.style.display='';
      $grand.disabled = false;
      categoriesData.filter(c => c.parent_category_id == $child.value)
          .forEach(c => $grand.add(new Option(c.category_name, c.category_id)));
    };
  }).catch(err => {
    console.error('카테고리 데이터를 불러오는 데 실패했습니다:', err);
  });
}

export function buildCategorySearchParams() {
  const params = new URLSearchParams();

  const $root  = document.getElementById('category_root');
  const $child = document.getElementById('category_child');
  const $grand = document.getElementById('category_grandchild');
  const $courseNameSearch = document.getElementById('course_name_search');
  const $college = document.getElementById('college');
  const $dept = document.getElementById('dept');

  if ($root && $child && $grand) {
    const cid = ($grand && $grand.value) || ($child && $child.value) || ($root && $root.value) || '';
    if (cid) params.append('category_id', cid);
  }
  if ($courseNameSearch && $courseNameSearch.value.trim()) {
    params.append('course_name', $courseNameSearch.value.trim());
  }
  if ($root && $root.selectedOptions.length && $root.selectedOptions[0].textContent === '전공') {
    if ($college && $college.value.trim()) params.append('college_name', $college.value.trim());
    if ($dept && $dept.value.trim()) params.append('dept_name', $dept.value.trim());
  }

  return params;
}