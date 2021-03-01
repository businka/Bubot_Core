import unittest
from bubot.Helper import Helper


class TestHelper(unittest.TestCase):
    base = {
        'list1': ['test1', 'test2'],
        'list2': ['test1', 'test2'],
        'list3': [1, 2],
        'list4': [1, 2],
        'str1': 'str2',
        'str2': 4,
        'str3': 'str2',
        'str4': 4,
        'dict1': {
            'list1': ['test1', 'test2'],
            'list2': ['test1', 'test2'],
            'list3': [1, 2],
            'list4': [1, 2],
            'str1': 'str2',
            'str2': 4,
            'str3': 'str2',
            'str4': 4,
            'list_dict1': [
                {
                    'list1': ['test1', 'test2'],
                    'list2': ['test1', 'test2'],
                    'list3': [1, 2],
                    'list4': [1, 2],
                    'str1': 'str2',
                    'str2': 4,
                    'str3': 'str2',
                    'str4': 4,
                },
                {
                    'list1': ['test1', 'test2'],
                    'list2': ['test1', 'test2'],
                    'list3': [1, 2],
                    'list4': [1, 2],
                    'str1': 'str2',
                    'str2': 4,
                    'str3': 'str2',
                    'str4': 4,
                }
            ],
            'list_dict2': [
                {
                    'list1': ['test1', 'test2'],
                    'list2': ['test1', 'test2'],
                    'list3': [1, 2],
                    'list4': [1, 2],
                    'str1': 'str2',
                    'id': 4,
                    'str3': 'str2',
                    'str4': 4,
                },
                {
                    'list1': ['test1', 'test2'],
                    'list2': ['test1', 'test2'],
                    'list3': [1, 2],
                    'list4': [1, 2],
                    'str1': 'str2',
                    'id': 5,
                    'str3': 'str2',
                    'str4': 4,
                }
            ],
        },
    }
    new = {
        'list1': ['test1', 'test21'],
        'list2': ['test1', 'test2'],
        'list3': [2, 2],
        'list4': [1, 2],
        'str1': 'str2',
        'str2': 4,
        'str3': 'str21',
        'str4': 5,
        'dict1': {
            'list1': ['test11', 'test2'],
            'list2': ['test1', 'test2'],
            'list3': [1, 22],
            'list4': [1, 2],
            'str1': 'str2',
            'str2': 4,
            'str3': 'str21',
            'str4': 5,
            'list_dict1': [
                {
                    'list1': ['test1', 'test21'],
                    'list2': ['test1', 'test2'],
                    'list3': [2, 2],
                    'list4': [1, 2],
                    'str1': 'str2',
                    'str2': 4,
                    'str3': 'str21',
                    'str4': 5,
                },
                {
                    'list1': ['test1', 'test2'],
                    'list2': ['test1', 'test2'],
                    'list3': [1, 2],
                    'list4': [1, 2],
                    'str1': 'str2',
                    'str2': 4,
                    'str3': 'str2',
                    'str4': 4,
                }
            ],
            'list_dict2': [
                {
                    'list1': ['test1', 'test21'],
                    'list2': ['test1', 'test2'],
                    'list3': [2, 2],
                    'list4': [1, 2],
                    'str1': 'str2',
                    'id': 4,
                    'str3': 'str21',
                    'str4': 5,
                },
                {
                    'list1': ['test1', 'test2'],
                    'list2': ['test1', 'test2'],
                    'list3': [1, 2],
                    'list4': [1, 2],
                    'str1': 'str2',
                    'id': 5,
                    'str3': 'str2',
                    'str4': 4,
                }
            ],
        },
    }

    def test_compare(self):
        pass

    def test_index(self):
        items = [
            {'di': '1', 'n': '1'},
            {'di': '2', 'n': '2'},
            {'di': '3', 'n': '3'},
        ]
        data = Helper.index_list(items, 'di')
        self.assertDictEqual(data, {'1': 0, '2': 1, '3': 2})
        self.assertRaises(KeyError, Helper.index_list, items, 'di1')


if __name__ == '__main__':
    unittest.main()
