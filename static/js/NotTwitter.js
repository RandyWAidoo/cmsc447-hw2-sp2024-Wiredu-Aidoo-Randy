function redirectToPage(page, event=null){
    if (!event || (event && event.keyCode === 13)){
        window.location.href = page;
    }
}

function changeActiveState(
    makeActiveId, makeActiveNextClassName, makeInactiveId, 
    makeInactiveNextClassName, maintain_active=true, fallbackClassName=null
){
    var makeActive = document.getElementById(makeActiveId);
    if (!maintain_active && makeActive.className === makeActiveNextClassName){
        makeActive.className = fallbackClassName;
    }else{
        makeActive.className = makeActiveNextClassName;
        document.getElementById(makeInactiveId).className = makeInactiveNextClassName;
    }
}