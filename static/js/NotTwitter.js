function changeActiveState(
    makeActiveId, makeActiveNextClassName, makeInactiveId, 
    makeInactiveNextClassName, maintain_active=true, fallbackClassName=null,
){
    var makeActive = document.getElementById(makeActiveId);
    if (!maintain_active && makeActive.className === makeActiveNextClassName){
        makeActive.className = fallbackClassName;
        return 0;
    }else{
        makeActive.className = makeActiveNextClassName;
        document.getElementById(makeInactiveId).className = makeInactiveNextClassName;
    }
    return 1;
}

function sendDisposition(
    postId, userPointsId, postPointsId, 
    postUsername, disposition,
) {
    fetch('/users/' + postUsername + '/post_service/disposition', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            "postId": postId, 
            "disposition": disposition
        })
    })
    .then(response => {return response.json();})
    .then(data => {
        var userPointsElem = document.getElementById(userPointsId);
        var postPointsElem = document.getElementById(postPointsId);
        userPointsElem.innerHTML = data["user_points"];
        postPointsElem.innerHTML = data["post_points"];
    })
    .catch(error => {
        var url = '/users/' + postUsername + '/post_service/disposition';
        console.error("Error occurred while fetching " + url + ":", error);
    });
}