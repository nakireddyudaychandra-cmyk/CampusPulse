import re


# ==========================================
# STOP WORDS
# ==========================================

STOP_WORDS = {
    "the",
    "is",
    "a",
    "an",
    "in",
    "on",
    "at",
    "and",
    "or",
    "to",
    "of",
    "not",
    "my",
    "our",
    "this",
    "that",
    "very",
    "with",
    "for",
    "from",
    "there",
    "problem",
    "issue"
}


# ==========================================
# CONVERT TEXT INTO KEYWORDS
# ==========================================

def get_keywords(text):

    text = text.lower()

    words = re.findall(r"[a-z]+", text)

    keywords = set()

    for word in words:

        if word not in STOP_WORDS and len(word) > 2:

            keywords.add(word)

    return keywords


# ==========================================
# CALCULATE SIMILARITY
# ==========================================

def calculate_similarity(text1, text2):

    words1 = get_keywords(text1)

    words2 = get_keywords(text2)


    if not words1 or not words2:

        return 0


    common_words = words1.intersection(words2)

    all_words = words1.union(words2)


    similarity = (
        len(common_words)
        /
        len(all_words)
    ) * 100


    return round(similarity, 2)


# ==========================================
# CHECK WHETHER TWO ISSUES ARE RELATED
# ==========================================

def are_related(issue1, issue2):

    # Location must match

    location1 = issue1["location"].lower().strip()

    location2 = issue2["location"].lower().strip()


    if location1 != location2:

        return False


    # Category must match

    category1 = issue1["category"].lower().strip()

    category2 = issue2["category"].lower().strip()


    if category1 != category2:

        return False


    # Compare title + description

    text1 = (
        issue1["title"]
        + " "
        + issue1["description"]
    )


    text2 = (
        issue2["title"]
        + " "
        + issue2["description"]
    )


    similarity = calculate_similarity(
        text1,
        text2
    )


    return similarity >= 20


# ==========================================
# FIND ISSUE CLUSTERS
# ==========================================

def find_clusters(issues):

    clusters = []


    used = set()


    for issue in issues:

        issue_id = issue["id"]


        if issue_id in used:

            continue


        cluster = [issue]


        used.add(issue_id)


        for other in issues:

            other_id = other["id"]


            if other_id in used:

                continue


            if are_related(issue, other):

                cluster.append(other)

                used.add(other_id)


        # Only show groups with 2 or more reports

        if len(cluster) >= 2:

            clusters.append(cluster)


    return clusters