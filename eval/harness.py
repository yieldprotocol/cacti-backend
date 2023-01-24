import eval.predict
import eval.evaluate_accuracy


def run():
    eval.predict.run()
    eval.evaluate_accuracy.run()


# Run this with: python3 -m eval.harness
if __name__ == "__main__":
    run()
