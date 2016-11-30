import re


class RE_helper():
    # example:
    # ' 1(result): addr:'
    # (' %s\((.*?)\): addr:' % port_id)
    @staticmethod
    def get_with_regex(self, regex, string):
        result = re.findall(regex,
                            string,
                            flags=re.DOTALL)
        if len(result) != 1:
            raise Exception('Got multiple or non matching result from regex '
                            '"%s" in string %s. result: %s'
                            % (regex, string, result))
        return result[0]
