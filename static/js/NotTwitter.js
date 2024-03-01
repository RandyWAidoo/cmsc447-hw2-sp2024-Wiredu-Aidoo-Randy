//Utility
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
    postId, userPointsIdPtrn, postPointsId, 
    postUsername, disposition,
){
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
        var userPointsElems = document.querySelectorAll('[id*="' + userPointsIdPtrn + '"]');
        var postPointsElem = document.getElementById(postPointsId);
        userPointsElems.forEach(el => {el.innerHTML = data["user_points"]});
        postPointsElem.innerHTML = data["post_points"];
    })
    .catch(error => {
        var url = '/users/' + postUsername + '/post_service/disposition';
        console.error("Error occurred while fetching " + url + ":", error);
    });
}


//Like and dislike(dispositions) handlers
disposition_event_handlers = {};

function handle_like(
    like_id, dislike_id, 
    likeActiveClassName, dislikeActiveClassName,
    likeInActiveClassName, dislikeInActiveClassName,
    _update_db, 
    postId, userPointsIdPtrn, postPointsId, 
    postUsername,
){
    if (!disposition_event_handlers.hasOwnProperty(like_id) 
        || typeof disposition_event_handlers[like_id] !== 'function'
    ){
        disposition_event_handlers[like_id] = function(
            like_id, dislike_id, 
            likeActiveClassName, dislikeActiveClassName,
            likeInActiveClassName, dislikeInActiveClassName,
            _update_db, 
            postId, userPointsIdPtrn, postPointsId, 
            postUsername,
        ){
            var disposition = 1;
            if (document.getElementById(dislike_id)
                .className === dislikeActiveClassName){
                disposition += 1;
            }
            isActive = changeActiveState(
                like_id, likeActiveClassName, 
                dislike_id, dislikeInActiveClassName, 
                maintain_active=false, fallbackClassName=likeInActiveClassName
            );
            if (!isActive){disposition = -1;}
            if (_update_db == 'True'){
                sendDisposition(
                    postId, userPointsIdPtrn, 
                    postPointsId, postUsername, disposition
                );
            }
        }
    }

    disposition_event_handlers[like_id](
        like_id, dislike_id, 
        likeActiveClassName, dislikeActiveClassName,
        likeInActiveClassName, dislikeInActiveClassName,
        _update_db, 
        postId, userPointsIdPtrn, postPointsId, 
        postUsername,
    )
}

function handle_dislike(
    dislike_id, like_id, 
    dislikeActiveClassName, likeActiveClassName, 
    dislikeInActiveClassName,likeInActiveClassName, 
    _update_db, 
    postId, userPointsIdPtrn, postPointsId, 
    postUsername,
){
    if (!disposition_event_handlers.hasOwnProperty(dislike_id) 
        || typeof disposition_event_handlers[dislike_id] !== 'function'
    ){
        disposition_event_handlers[dislike_id] = function(
            dislike_id, like_id, 
            dislikeActiveClassName, likeActiveClassName, 
            dislikeInActiveClassName,likeInActiveClassName, 
            _update_db, 
            postId, userPointsIdPtrn, postPointsId, 
            postUsername,
        ){
            var disposition = -1;
            if (document.getElementById(like_id)
                .className === likeActiveClassName){
                disposition += -1;
            }
            isActive = changeActiveState(
                dislike_id, dislikeActiveClassName, 
                like_id, likeInActiveClassName, 
                maintain_active=false, fallbackClassName=dislikeInActiveClassName
            );
            if (!isActive){disposition = 1;}
            if (_update_db == 'True'){
                sendDisposition(
                    postId, userPointsIdPtrn, 
                    postPointsId, postUsername, disposition
                );
            }
        }   
    }

    disposition_event_handlers[dislike_id](
        dislike_id, like_id, 
        dislikeActiveClassName, likeActiveClassName, 
        dislikeInActiveClassName,likeInActiveClassName, 
        _update_db, 
        postId, userPointsIdPtrn, postPointsId, 
        postUsername,
    )
}

function delete_post(postId){
    fetch("/users/post_service/delete/" + postId + "/")
    .then(response => {
        document.getElementById(postId).remove();
    })
    .catch(error => {
        var url = "/users/post_service/delete/" + postId + "/";
        console.error("Error occurred while fetching " + url + ":", error);
    });
}