from sqlalchemy import (
    update,
    exists,
    not_,
    func
)
from sqlalchemy.orm import (
    aliased
)
import datetime, math, random, requests
from database import (
    User,
    Post,
    Session,
    followers_table,
    blocks_table
)
from .post_service import (
    get_users_last_posts,
    get_users_last_comments,
    get_post
)


def seen(user:User):
    session = Session()
    stmt = (
        update(User).
        where(User.userID == user.userID).
        values(lastseen=datetime.datetime.now().strftime("%Y%m%d%H%M"))
    )
    # Execute the update statement
    result = session.execute(stmt)
    # Commit the changes to the database
    session.commit()
    if result.rowcount > 0:
        return True
    return False


def following_posts(user:User):
    session = Session()
    lastseen = user.lastseen

    posts = (
        session.query(Post)
        .join(followers_table, followers_table.c.followed_id == Post.authorID)
        .filter(
            followers_table.c.follower_id == user.userID,  # Only include followed users
            Post.date > lastseen,  # Only include posts after the specified datetime
            Post.parent == None
        )
        .order_by(Post.date.desc())  # Order posts by descending date
        .all()
    )
    random.shuffle(posts)
    return posts


def get_interests(user:User):
    score = {}
    for i in user.get_likes(15):
        if i.category not in score:
            score[i.category] = 7
        else:
            score[i.category] += 7
    for i in get_users_last_comments(user.userID, 10):
        if i.category not in score:
            score[i.category] = 5
        else:
            score[i.category] += 5
    for i in get_users_last_posts(user.userID, 5):
        if i.category not in score:
            score[i.category] = 5
        else:
            score[i.category] += 5
    return score
    

def calculate_recency_score(event_time, current_time, decay_factor=0.05):
    event_time = datetime.datetime.strptime(event_time, "%Y%m%d%H%M")
    # Calculate the time difference in seconds
    time_diff = current_time - event_time
    time_diff = time_diff.total_seconds()
    # Calculate the recency score using an exponential decay function
    recency_score = math.exp(-decay_factor * time_diff)    
    return 5*recency_score


def prefered_posts(user:User, n=25):
    session = Session()
    result = []

    now = datetime.datetime.now()
    fourteen_days_ago = (now - datetime.timedelta(days=14)).strftime("%Y%m%d%H%M")
    blocked_alias = aliased(User)
    intrests = get_interests(user)
    
    # getting recent posts
    recent_posts = session.query(Post).filter(
        Post.date >= fourteen_days_ago,
        not_(
            exists().where(
                (blocked_alias.userID == Post.authorID) &  # Post author
                (blocked_alias.userID == blocks_table.c.blocked_id) &  # is in the blocked table
                (blocks_table.c.blocker_id == user.userID)  # by the authenticated user
            )
        ),
        Post.authorID != user.userID,
        Post.parent == None
    ).all()
    
    random.shuffle(recent_posts)
    # calculate preference score
    for post in recent_posts:
        if post.category:
            score = intrests[post.category] + calculate_recency_score(post.date, current_time=now) + (len(post.likes)*0.2)
            result.append((score, post))
        else:
            score = calculate_recency_score(post.date, current_time=now) + (len(post.likes)*0.25)
            result.append((score, post))
    # sort and choose n posts by preference score
    sorted_pairs = sorted(result, key=lambda pair: pair[0], reverse=True)
    return [p[1] for p in sorted_pairs[-n:]]


def mix_lists_preserving_order(list1, list2):
    # Create a combined list of elements, each associated with a list identifier
    combined = [(1, elem) for elem in list1] + [(2, elem) for elem in list2]
    # Shuffle the combined list to mix elements from both lists
    random.shuffle(combined)
    # Create an output list, ensuring the order within each list is preserved
    result = []
    for _, elem in sorted(combined, key=lambda x: (x[0], list1.index(x[1]) if x[0] == 1 else list2.index(x[1]))):
        result.append(elem)
    return result


def homepage_feed(user:User):
    list1 = following_posts(user)
    list2 = prefered_posts(user)
    return mix_lists_preserving_order(list1, list2)


def handle_post_category(postid):
    session = Session()  
    try:
        p = get_post(postid)
        if p:
            try:
                req = requests.post(
                    "https://palmix.pythonanywhere.com/sampader-category-gemini",
                    json={"input": p.text},
                )
                c = req.text
            except Exception as e:
                print(f"Category Handle Error: {str(e)}")
                c = "test"
            # Update category
            p.category = c
            session.commit()
    except:
        session.rollback()


def get_followed_by_followings(user_id, limit=5):
    session = Session()
    # Alias for the User table to distinguish between the user and the followed users
    Follower = aliased(User)
    FollowedByFollowings = aliased(User)

    # Query to find users that are followed by the user's followings
    followed_by_followings = (
        session.query(FollowedByFollowings, func.count(FollowedByFollowings.userID).label('count'))
        .join(followers_table, FollowedByFollowings.userID == followers_table.c.followed_id)
        .join(Follower, Follower.userID == followers_table.c.follower_id)
        .filter(followers_table.c.follower_id.in_(
            # Subquery to find the people the user is following
            session.query(followers_table.c.followed_id)
            .filter(followers_table.c.follower_id == user_id)
        ))
        .filter(FollowedByFollowings.userID != user_id)  # Exclude the user themselves from the results
        .filter(not_(
            exists().where(
                (blocks_table.c.blocked_id == FollowedByFollowings.userID) &  # The followed user
                (blocks_table.c.blocker_id == user_id)  # is blocked by the current user
            )
        ))
        .group_by(FollowedByFollowings.userID)
        .order_by(func.count(FollowedByFollowings.userID).desc())  # Sort by the most followed
        .limit(limit)
        .all()
    )
    return [i[0] for i in followed_by_followings]


def get_most_followed_users(limit=5):
    session = Session()
    # Query to get users with the most followers
    most_followed_users = (
        session.query(User, func.count(followers_table.c.follower_id).label('follower_count'))
        .join(followers_table, User.userID == followers_table.c.followed_id)
        .group_by(User.userID)
        .order_by(func.count(followers_table.c.follower_id).desc())  # Order by follower count in descending order
        .limit(limit)  # Limit to the top 'n' users
        .all()
    )
    return [i[0] for i in most_followed_users]


def suggest_people(userid):
    res = get_most_followed_users()
    res = res + get_followed_by_followings(userid)
    return res
