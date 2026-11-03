class Solution(object):
    def longestPalindrome(self, s):
        """
        :type s: str
        :rtype: str
        """
        mystr = s
        word = mystr[0]
        maxlen = 0
        substrings = []
        for i in range(0, len(s)-1):
            for j in range(i, len(s)):
                substrings.append(mystr[i:j+1])
        for item in substrings:
            if item == item[::-1]:
                if maxlen < len(item):
                    maxlen = len(item)
                    word = item 
        #print(substrings)
        return word 


sol = Solution()
print(sol.longestPalindrome("babad"))  # Output: "bab" or "aba"
print(sol.longestPalindrome("cbbd"))   # Output: "bb"
print(sol.longestPalindrome("a"))      # Output: "a"
print(sol.longestPalindrome("ac"))     # Output: "a" or "c"
print(sol.longestPalindrome("bb"))  # Output: "bb"
