from unittest import TestCase
from base import PMMLBaseEstimator, Interval, Category
from sklearn.datasets import load_iris
import pandas as pd
import numpy as np
from io import StringIO
from collections import namedtuple

# Parameters
pair = [0, 1]

# Load data
iris = load_iris()

# We only take the two corresponding features
X = pd.DataFrame(iris.data[:, pair])
X.columns = np.array(iris.feature_names)[pair]
y = pd.Series(np.array(iris.target_names)[iris.target])
y.name = "Class"
df = pd.concat([X, y], axis=1)


class TestBase(TestCase):

  def setUp(self):
    pass


  def test_evaluate_feature_mapping(self):
    clf = PMMLBaseEstimator(pmml=StringIO("""
    <PMML xmlns="http://www.dmg.org/PMML-4_3" version="4.3">
      <DataDictionary>
        <DataField name="Class" optype="categorical" dataType="string">
          <Value value="setosa"/>
          <Value value="versicolor"/>
          <Value value="virginica"/>
        </DataField>
        <DataField name="sepal length (cm)" optype="continuous" dataType="float"/>
        <DataField name="sepal width (cm)" optype="continuous" dataType="float"/>
      </DataDictionary>
      <TransformationDictionary>
        <DerivedField name="integer(sepal length (cm))" optype="continuous" dataType="integer">
          <FieldRef field="sepal length (cm)"/>
        </DerivedField>
        <DerivedField name="double(sepal width (cm))" optype="continuous" dataType="double">
          <FieldRef field="sepal width (cm)"/>
        </DerivedField>
      </TransformationDictionary>
      <TreeModel/>
    </PMML>
    """))

    Result = namedtuple('Result', 'column type')
    tests = {
      'Class':                     Result(column='Class', type=Category),
      'sepal length (cm)':         Result(column='sepal length (cm)', type=float),
      'sepal width (cm)':          Result(column='sepal width (cm)', type=float),
      'integer(sepal length (cm))':Result(column='sepal length (cm)', type=int),
      'double(sepal width (cm))':  Result(column='sepal width (cm)', type=float)
    }

    for i in range(0, len(df)):
      for feature, result in tests.items():
        column, mapping = clf.field_mapping[feature]
        assert column == result.column
        mapped_value = mapping(df.iloc[i][column])
        assert type(mapped_value) == result.type

        if result.type == Category:
          assert mapped_value.value == df.iloc[i][column]
          assert mapped_value.categories == ["setosa", "versicolor", "virginica"]
        else:
          assert mapped_value == result.type(df.iloc[i][column])


  def test_parse_type_value_continuous(self):
    template = """
    <PMML xmlns="http://www.dmg.org/PMML-4_3" version="4.3">
      <DataDictionary>
        <DataField name="test" optype="{}" dataType="{}"/>
      </DataDictionary>
    </PMML>"""

    values = ["1234", 1234, 12.34, True]
    types = [
      ['continuous', 'integer', int],
      ['continuous', 'float', float],
      ['continuous', 'double', float],
      ['continuous', 'boolean', bool]
    ]

    for value in values:
      for type in types:
        optype, pmml_type, data_type = type
        clf = PMMLBaseEstimator(pmml=StringIO(template.format(optype, pmml_type)))

        data_dictionary = clf.find(clf.root, "DataDictionary")
        data_field = clf.find(data_dictionary, "DataField")
        result = clf.parse_type(value, data_field)

        assert isinstance(result, data_type)


  def test_parse_type_value_exception(self):
    template = """
    <PMML xmlns="http://www.dmg.org/PMML-4_3" version="4.3">
      <DataDictionary>
        <DataField name="test" optype="{}" dataType="{}"/>
      </DataDictionary>
    </PMML>"""

    # Test invalid data type
    clf = PMMLBaseEstimator(pmml=StringIO(template.format("continuous", "does_not_exist")))
    data_dictionary = clf.find(clf.root, "DataDictionary")
    data_field = clf.find(data_dictionary, "DataField")

    with self.assertRaises(Exception) as cm: clf.parse_type("test", data_field)
    assert str(cm.exception) == "Unsupported data type."

    # Test invalid operation type
    clf = PMMLBaseEstimator(pmml=StringIO(template.format("does_not_exist", "string")))
    data_dictionary = clf.find(clf.root, "DataDictionary")
    data_field = clf.find(data_dictionary, "DataField")

    with self.assertRaises(Exception) as cm: clf.parse_type("test", data_field)
    assert str(cm.exception) == "Unsupported operation type."


  def test_parse_type_value_categorical(self):
      template = """
      <PMML xmlns="http://www.dmg.org/PMML-4_3" version="4.3">
        <DataDictionary>
          <DataField name="Class" optype="categorical" dataType="string">
            <Value value="setosa"/>
            <Value value="versicolor"/>
            <Value value="virginica"/>
          </DataField>
        </DataDictionary>
      </PMML>"""

      clf = PMMLBaseEstimator(pmml=StringIO(template))
      data_dictionary = clf.find(clf.root, "DataDictionary")
      data_field = clf.find(data_dictionary, "DataField")

      with self.assertRaises(Exception) as cm: clf.parse_type("not_in_category", data_field)
      assert str(cm.exception) == "Invalid categorical value."
      assert clf.parse_type("setosa", data_field) == "setosa"
      assert clf.parse_type("versicolor", data_field) == "versicolor"
      assert clf.parse_type("virginica", data_field) == "virginica"


  def test_parse_type_value_ordinal(self):
    template = """
      <PMML xmlns="http://www.dmg.org/PMML-4_3" version="4.3">
        <DataDictionary>
          <DataField name="Volume" optype="ordinal" dataType="string">
            <Value value="loud"/>
            <Value value="louder"/>
            <Value value="insane"/>
          </DataField>
        </DataDictionary>
      </PMML>"""

    clf = PMMLBaseEstimator(pmml=StringIO(template))
    data_dictionary = clf.find(clf.root, "DataDictionary")
    data_field = clf.find(data_dictionary, "DataField")

    with self.assertRaises(Exception)as cm: clf.parse_type("not_in_category", data_field)
    assert str(cm.exception) == "Invalid ordinal value."
    assert clf.parse_type("loud", data_field) == "loud"
    assert clf.parse_type("louder", data_field) == "louder"
    assert clf.parse_type("insane", data_field) == "insane"

    assert clf.parse_type("loud", data_field) < clf.parse_type("louder", data_field)
    assert clf.parse_type("louder", data_field) < clf.parse_type("insane", data_field)


  def test_parse_type_interval(self):
    template = """
    <PMML xmlns="http://www.dmg.org/PMML-4_3" version="4.3">
      <DataDictionary>
        <DataField name="test" optype="ordinal" dataType="float">
          <Interval closure="openOpen" rightMargin="1"/>
          <Interval closure="openClosed" leftMargin="1" rightMargin="1.5"/>
          <Interval closure="openOpen" leftMargin="1.5" rightMargin="2.5"/>
          <Interval closure="closedOpen" leftMargin="2.5" rightMargin="3.5"/>
          <Interval closure="closedClosed" leftMargin="3.5" />
        </DataField>
      </DataDictionary>
    </PMML>"""

    clf = PMMLBaseEstimator(pmml=StringIO(template))
    data_dictionary = clf.find(clf.root, "DataDictionary")
    data_field = clf.find(data_dictionary, "DataField")

    assert clf.parse_type(-1, data_field) == Interval(-1, rightMargin=1, closure='openOpen')
    with self.assertRaises(Exception): clf.parse_type(1, data_field)
    assert clf.parse_type(2, data_field) == Interval(2, leftMargin=1.5, rightMargin=2.5, closure='openOpen')
    assert clf.parse_type(2.5, data_field) == Interval(2.5, leftMargin=2.5, rightMargin=3.5, closure='closedOpen')
    assert clf.parse_type(3.5, data_field) == Interval(3.5, leftMargin=3.5, closure='closedClosed')


  def test_interval_exception(self):
    with self.assertRaises(Exception): Interval(1, closure='openOpen')


  def test_category_exception(self):
    with self.assertRaises(Exception): Category('1', [1, 2])