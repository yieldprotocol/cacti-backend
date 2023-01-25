import eval.predict
import eval.evaluate_accuracy
import eval.evaluate_personality


def run():
    eval.predict.run()
    eval.evaluate_accuracy.run()
    eval.evaluate_personality.run()


# Run this with: python3 -m eval.harness
if __name__ == "__main__":
    run()
